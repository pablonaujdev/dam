import base64
from datetime import date
from unittest.mock import patch

from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, new_test_user, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'jh_report_presets19')
class TestJhInvoiceReportPresets(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_company = cls.env['res.company'].create({'name': 'JH preset company'})
        cls.owner = new_test_user(cls.env, login='jh_preset_owner',
            groups='base.group_user,base.group_multi_company,account.group_account_user',
            company_id=cls.env.company.id,
            company_ids=[Command.set((cls.env.company | cls.other_company).ids)])
        cls.other_user = new_test_user(cls.env, login='jh_preset_other',
            company_id=cls.env.company.id, company_ids=[Command.set(cls.env.company.ids)])

    def _wizard_model(self, company=None):
        company = company or self.env.company
        return self.env['jh.invoice.report.wizard'].with_user(self.owner).with_context(
            allowed_company_ids=company.ids)

    def _wizard(self, **values):
        return self._wizard_model().create(dict(jh_preset_name='Ventas MIAC', **values))

    def test_save_load_explicit_update_delete(self):
        commission = self.env['commission'].create({'name': 'Preset commission', 'fix_qty': 5})
        agent = self.env['res.partner'].create({'name': 'Preset agent', 'agent': True, 'commission_id': commission.id})
        wizard = self._wizard(jh_period='manual', date_from='2026-01-01', date_to='2026-01-31',
            product_ids=[Command.set(self.product_a.ids)], partner_ids=[Command.set(self.partner_a.ids)],
            agents_ids=[Command.set(agent.ids)],
            product_categ_ids=[Command.set(self.product_a.categ_id.ids)], partner_type='customer',
            state='posted', move_type='out_invoice', export_format='csv', show_jh_cost=True)
        action = wizard.action_jh_save_preset()
        preset = wizard.jh_preset_id
        self.assertEqual(action['res_id'], wizard.id)
        self.assertEqual((preset.jh_user_id, preset.jh_company_id), (self.owner, self.env.company))
        self.assertNotIn('file_data', preset.jh_settings)
        wizard.show_jh_cost = False
        self.assertTrue(preset.jh_settings['show_jh_cost'])
        loaded = self._wizard_model().create(wizard._jh_preset_values(preset))
        self.assertEqual(loaded.date_from, date(2026, 1, 1))
        self.assertEqual(loaded.product_ids, self.product_a)
        self.assertEqual(loaded.partner_ids, self.partner_a)
        self.assertEqual(loaded.agents_ids, agent)
        self.assertEqual(loaded.product_categ_ids, self.product_a.categ_id)
        self.assertEqual((loaded.partner_type, loaded.state, loaded.move_type, loaded.export_format),
            ('customer', 'posted', 'out_invoice', 'csv'))
        wizard.action_jh_update_preset()
        self.assertFalse(preset.jh_settings['show_jh_cost'])
        preset_id = preset.id
        wizard.action_jh_delete_preset()
        self.assertFalse(self.env['jh.invoice.report.preset'].browse(preset_id).exists())
        self.assertFalse(wizard.jh_preset_id)

    def test_default_and_relative_periods(self):
        wizard = self._wizard(jh_period='previous_month', jh_preset_default=True)
        wizard.action_jh_save_preset()
        self.assertNotIn('date_from', wizard.jh_preset_id.jh_settings)
        with patch.object(fields.Date, 'context_today', return_value=date(2028, 3, 12)):
            defaults = self._wizard_model().default_get(['jh_preset_id', 'date_from', 'date_to'])
            self.assertEqual(defaults['jh_preset_id'], wizard.jh_preset_id.id)
            self.assertEqual((defaults['date_from'], defaults['date_to']), (date(2028, 2, 1), date(2028, 2, 29)))
            self.assertEqual(wizard._jh_period_dates('current_month'),
                {'date_from': date(2028, 3, 1), 'date_to': date(2028, 3, 12)})
            self.assertEqual(wizard._jh_period_dates('current_year'),
                {'date_from': date(2028, 1, 1), 'date_to': date(2028, 3, 12)})

    def test_unique_names_and_last_default_in_batch(self):
        model = self.env['jh.invoice.report.preset'].with_user(self.owner)
        presets = model.create([
            {'jh_name': name, 'jh_settings': {'jh_period': 'current_month'}, 'jh_is_default': True}
            for name in ('First', 'Last')])
        self.assertEqual(presets.filtered('jh_is_default'), presets[-1])
        presets.write({'jh_is_default': True})
        self.assertEqual(presets.filtered('jh_is_default'), presets[-1])
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            model.create({'jh_name': 'First', 'jh_settings': {'jh_period': 'current_month'}})

    def test_privacy_and_owner_cannot_be_transferred(self):
        wizard = self._wizard()
        wizard.action_jh_save_preset()
        preset = wizard.jh_preset_id
        foreign = preset.with_user(self.other_user)
        self.assertFalse(foreign.search([('id', '=', preset.id)]))
        for operation in ('read', 'write', 'unlink'):
            with self.assertRaises(AccessError), self.cr.savepoint():
                foreign.check_access(operation)
        with self.assertRaises(AccessError), self.cr.savepoint():
            preset.write({'jh_user_id': self.other_user.id})
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.env['jh.invoice.report.preset'].with_user(self.other_user).create({
                'jh_name': 'Foreign', 'jh_user_id': self.owner.id, 'jh_settings': {'jh_period': 'manual'}})

    def test_company_isolation_and_inactive_company_notice(self):
        wizard = self._wizard(jh_preset_default=True)
        wizard.action_jh_save_preset()
        preset = wizard.jh_preset_id
        self.assertFalse(self._wizard_model(self.other_company).default_get(['jh_preset_id']).get('jh_preset_id'))
        with self.assertRaises(UserError):
            self._wizard_model(self.other_company)._jh_preset_values(preset)
        settings = dict(preset.jh_settings, company_ids=(self.env.company | self.other_company).ids)
        preset.jh_settings = settings
        defaults = self._wizard_model().default_get(['jh_preset_id', 'jh_preset_notice'])
        self.assertFalse(defaults.get('jh_preset_id'))
        self.assertTrue(defaults['jh_preset_notice'])
        model = self._wizard_model().with_context(allowed_company_ids=(self.env.company | self.other_company).ids)
        loaded = model.create(model._jh_preset_values(preset))
        self.assertEqual(loaded.company_ids, self.env.company | self.other_company)
        with self.assertRaises(UserError):
            loaded.with_context(allowed_company_ids=self.env.company.ids)._jh_configuration_values()

    def test_deleted_and_invalid_filters_show_default_notice(self):
        partner = self.env['res.partner'].create({'name': 'Temporary preset partner'})
        wizard = self._wizard(jh_preset_default=True, partner_ids=[Command.set(partner.ids)])
        wizard.action_jh_save_preset()
        partner.unlink()
        self.assertTrue(self._wizard_model().default_get(['jh_preset_notice'])['jh_preset_notice'])
        for settings in ([1], {'partner_ids': ['invalid']}, {'export_format': 'obsolete'},
                {'jh_period': 'manual', 'date_from': 'invalid'},
                {'jh_period': 'manual', 'date_from': '2026-02-01', 'date_to': '2026-01-01'}):
            wizard.jh_preset_id.jh_settings = settings
            with self.assertRaises(UserError):
                wizard._jh_preset_values(wizard.jh_preset_id)

    def test_form_onchange_and_management_action(self):
        wizard = self._wizard(export_format='csv', show_jh_cost=True)
        wizard.action_jh_save_preset()
        with Form(self._wizard_model()) as form:
            form.jh_preset_id = wizard.jh_preset_id
            self.assertEqual(form.export_format, 'csv')
            self.assertTrue(form.show_jh_cost)
            form.jh_period = 'manual'
            form.date_from = '2026-01-01'
            form.date_to = '2026-01-31'
        action = wizard.action_jh_manage_presets()
        self.assertEqual(action['view_mode'], 'list')
        self.assertIn(('jh_user_id', '=', self.owner.id), action['domain'])
        self.assertEqual(action['res_model'], 'jh.invoice.report.preset')

    def test_saved_filters_generate_csv_and_xlsx(self):
        invoice = self.init_invoice('out_invoice', partner=self.partner_a,
            invoice_date=fields.Date.today(), products=self.product_a, amounts=[123], post=True)
        wizard = self._wizard(jh_period='manual', date_from=invoice.invoice_date, date_to=invoice.invoice_date,
            partner_ids=[Command.set(self.partner_a.ids)], product_ids=[Command.set(self.product_a.ids)],
            move_type='out_invoice', state='posted', export_format='csv')
        wizard.action_jh_save_preset()
        for export_format in ('csv', 'xlsx'):
            loaded = self._wizard_model().create(wizard._jh_preset_values(wizard.jh_preset_id))
            loaded.export_format = export_format
            loaded.action_generate_report()
            self.assertEqual(loaded.state_wizard, 'done')
            output = base64.b64decode(loaded.file_data)
            self.assertTrue(output)
            self.assertTrue(loaded.file_name.endswith('.' + export_format))
            if export_format == 'xlsx':
                self.assertTrue(output.startswith(b'PK'))
            else:
                self.assertIn(self.partner_a.name, output.decode('utf-8-sig'))
