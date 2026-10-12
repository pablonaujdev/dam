"""Commission quantities, without changing native settlement calculations."""
from pathlib import Path

from lxml import html

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tools import config
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged('post_install', '-at_install', 'miac_quantity19')
class TestMiacQuantity19(AccountTestInvoicingCommon):
    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.quick_ref('commission_oca.group_commission_manager')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.commission = cls.env['commission'].create({'name': 'QUANTITY19 10%', 'fix_qty': 10})
        cls.agents = cls.env['res.partner'].create([
            {'name': name, 'agent': True, 'commission_id': cls.commission.id, 'lang': 'en_US'}
            for name in ('QUANTITY19 Agent A', 'QUANTITY19 Agent B')])
        cls.product = cls.env['product.product'].create({'name': 'QUANTITY19 Product', 'type': 'service'})

    def invoice(self, quantities, agents=None):
        agents = agents if agents is not None else self.agents[:1]
        return self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [Command.create({'product_id': self.product.id,
                'quantity': quantity, 'price_unit': 100,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [Command.clear()],
                'agent_ids': [Command.create({'agent_id': agent.id, 'commission_id': self.commission.id})
                              for agent in agents]}) for quantity in quantities],
        })

    def settlement(self, agent_line=None, **values):
        return self.env['commission.settlement'].create({
            'agent_id': agent_line.agent_id.id if agent_line else self.agents[0].id,
            'date_from': fields.Date.today(), 'date_to': fields.Date.today(),
            'settlement_type': 'sale_invoice' if agent_line else 'manual',
            'line_ids': [Command.create({'invoice_agent_line_id': agent_line.id,
                'date': agent_line.invoice_date, 'commission_id': agent_line.commission_id.id,
                'settled_amount': agent_line.amount})] if agent_line else [
                Command.create({'date': fields.Date.today(), 'commission_id': self.commission.id,
                                'settled_amount': 37})], **values,
        })

    def test_stored_quantity_precision_and_native_values(self):
        invoice = self.invoice([3, 2.375, 0, -1.5])
        lines = self.env['commission.settlement.line']
        for invoice_line in invoice.invoice_line_ids:
            lines |= self.settlement(invoice_line.agent_ids).line_ids
        expected = invoice.invoice_line_ids.mapped('quantity')
        self.assertEqual(lines.mapped('invoiced_quantity'), expected)
        field = lines._fields['invoiced_quantity']
        self.assertTrue(field.store)
        self.assertTrue(field.readonly)
        self.assertEqual(field.related, 'invoice_line_id.quantity')
        self.assertEqual(field.get_digits(self.env), invoice.invoice_line_ids._fields['quantity'].get_digits(self.env))
        self.env.flush_all()
        lines.invalidate_recordset(['invoiced_quantity'])
        self.assertEqual(lines.mapped('invoiced_quantity'), expected)

    def test_quantity_and_source_changes_follow_invoice(self):
        invoice = self.invoice([2, 7.125])
        settlement = self.settlement(invoice.invoice_line_ids[0].agent_ids)
        # Cancelled settlements allow source commission changes through native OCA checks.
        settlement.action_cancel()
        invoice.invoice_line_ids[0].quantity = 4.75
        self.assertEqual(settlement.line_ids.invoiced_quantity, 4.75)
        settlement.line_ids.invoice_agent_line_id = invoice.invoice_line_ids[1].agent_ids
        self.assertEqual(settlement.line_ids.invoiced_quantity, invoice.invoice_line_ids[1].quantity)
        settlement.line_ids.invoice_agent_line_id = False
        self.assertEqual(settlement.line_ids.invoiced_quantity, 0)

    def test_manual_settlement_has_zero_and_preserves_amount(self):
        settlement = self.settlement()
        self.assertEqual(settlement.line_ids.invoiced_quantity, 0)
        self.assertEqual(settlement.total, 37)

    def test_multiple_agents_do_not_split_quantity_or_amount(self):
        invoice = self.invoice([2.5], self.agents)
        settlements = self.env['commission.settlement']
        original = invoice.invoice_line_ids.agent_ids.mapped('amount')
        for agent_line in invoice.invoice_line_ids.agent_ids:
            settlements |= self.settlement(agent_line)
        self.assertEqual(settlements.line_ids.mapped('invoiced_quantity'), [2.5, 2.5])
        self.assertEqual(invoice.invoice_line_ids.agent_ids.mapped('amount'), original)
        self.assertEqual(settlements.mapped('total'), original)

    def test_refund_keeps_positive_quantity_and_negative_commission(self):
        invoice = self.invoice([2.5])
        invoice.action_post()
        original = self.settlement(invoice.invoice_line_ids.agent_ids)
        refund = invoice._reverse_moves(default_values_list=[{'invoice_date': fields.Date.today()}])
        refund.action_post()
        settlement = self.settlement(refund.invoice_line_ids.agent_ids)
        self.assertEqual(settlement.line_ids.invoiced_quantity, 2.5)
        self.assertEqual(settlement.line_ids.invoiced_quantity, refund.invoice_line_ids.quantity)
        self.assertLess(settlement.total, 0)
        self.assertEqual(settlement.total, -original.total)

    def test_column_composition_groups_and_translation(self):
        view = self.env.ref('account_commission_oca.view_settlement_form')
        arch = view._get_combined_arch()
        nodes = arch.xpath('//field[@name="line_ids"]/list/field[@name="invoiced_quantity"]')
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].getprevious().get('name'), 'invoice_line_id')
        self.assertEqual(nodes[0].get('groups'), 'account.group_account_invoice')
        self.assertIn('sale_invoice', nodes[0].get('column_invisible'))
        self.assertEqual(self.env.ref('miac_quantity_commission.commission_settlement_invoiced_quantity_view_form_inherit').priority, 50)
        description = self.env['commission.settlement.line'].with_context(lang='es_ES').fields_get(['invoiced_quantity'])
        self.assertEqual(description['invoiced_quantity']['string'], 'Cantidad Facturada')
        user = self.env['res.users'].create({'name': 'QUANTITY19 Commission reader',
            'login': 'quantity19-reader', 'group_ids': [Command.set(self.env.ref('commission_oca.group_commission_user').ids)]})
        public_arch = self.env['commission.settlement'].with_user(user).get_view(
            view_id=self.env.ref('commission_oca.view_settlement_form').id, view_type='form')['arch']
        self.assertNotIn('name="invoiced_quantity"', public_arch)

    def test_native_pdf_quantity_and_commission_unchanged(self):
        settlement = self.settlement(self.invoice([2.375]).invoice_line_ids.agent_ids)
        before = settlement.total, settlement.line_ids.settled_amount
        engine = self.env['ir.actions.report'].with_context(discard_logo_check=True, force_report_rendering=True)
        content = engine._render_qweb_html('commission_oca.action_report_settlement', settlement.ids)[0]
        page = html.fromstring(content)
        self.assertEqual(len(page.xpath('//th[contains(normalize-space(), "Quantity")]')), 1)
        self.assertIn('2.38', page.text_content())
        folder = Path('/var/lib/odoo/quantity-commission19-validation')
        folder.mkdir(exist_ok=True)
        (folder / 'settlement.html').write_bytes(content)
        self.env['ir.config_parameter'].sudo().set_param('report.url', 'http://127.0.0.1:%s' % config['http_port'])
        with self.allow_pdf_render():
            pdf = engine._render_qweb_pdf('commission_oca.action_report_settlement', settlement.ids)[0]
        self.assertTrue(pdf.startswith(b'%PDF'))
        (folder / 'settlement.pdf').write_bytes(pdf)
        self.assertEqual(before, (settlement.total, settlement.line_ids.settled_amount))
