# Part of Avannubo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form, new_test_user, tagged
from odoo.tools import mute_logger
from odoo.addons.sale_purchase.tests.common import TestCommonSalePurchaseNoChart


@tagged('post_install', '-at_install', 'license_notification19')
class TestLicensePurchaseNotification(TestCommonSalePurchaseNoChart):
    @classmethod
    def get_default_groups(cls):
        return (super().get_default_groups()
                | cls.env.ref('purchase.group_purchase_manager')
                | cls.env.ref('stock.group_stock_manager'))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = cls.env['sale.subscription.plan'].create({
            'name': 'License notice monthly', 'billing_period_value': 1,
            'billing_period_unit': 'month',
        })
        cls.service_purchase_1.recurring_invoice = True
        cls.service_purchase_2.recurring_invoice = True
        cls.non_recurring = cls.env['product.product'].create({
            'name': 'One-off purchased service', 'recurring_invoice': False,
            'type': 'service', 'service_to_purchase': True, 'invoice_policy': 'delivery',
            'taxes_id': False,
            'seller_ids': [Command.create({'partner_id': cls.partner_vendor_service.id, 'price': 20})],
        })
        cls.recipient = cls.env['res.partner'].create({
            'name': 'License recipient', 'email': 'licenses@example.invalid',
            'lang': 'en_US',
        })
        cls.env.company.notify_purchase_license_id = cls.recipient
        cls.template = cls.env.ref(
            'miac_sale_purchase_notification.email_template_sale_purchase_license')

    def setUp(self):
        super().setUp()
        self.startPatcher(patch.object(
            type(self.env['ir.mail_server']), 'send_email',
            side_effect=AssertionError('SMTP must not run during confirmation'),
        ))

    def _order(self, products=None, company=None):
        products = products or [self.service_purchase_1]
        company = company or self.env.company
        return self.env['sale.order'].with_company(company).create({
            'partner_id': self.partner_a.id, 'company_id': company.id,
            'plan_id': self.plan.id if any(p.recurring_invoice for p in products) else False,
            'order_line': [Command.create({
                'product_id': product.id, 'product_uom_qty': 2,
                'price_unit': 50, 'tax_ids': False,
            }) for product in products],
        })

    def _mails(self, order):
        return self.env['mail.mail'].sudo().search([
            ('model', '=', 'sale.order'), ('res_id', '=', order.id),
        ])

    def _assert_notice(self, order, recipient=None):
        mails = self._mails(order)
        self.assertEqual(len(mails), 1, str(order.message_ids.mapped('body')))
        self.assertEqual(mails.recipient_ids, recipient or self.recipient)
        self.assertFalse(mails.email_to)
        self.assertFalse(mails.email_cc)
        self.assertEqual(mails.state, 'outgoing')
        self.assertEqual(order.state, 'sale')
        self.assertTrue(order.order_line.sudo().purchase_line_ids)
        return mails

    def _assert_informative_failure(self, order, text):
        self.assertEqual(order.state, 'sale')
        self.assertTrue(order.order_line.sudo().purchase_line_ids)
        self.assertFalse(self._mails(order))
        notes = order.message_ids.filtered(lambda message: text in message.body)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes.subtype_id, self.env.ref('mail.mt_note'))
        self.assertFalse(notes.notification_ids)

    def test_one_notice_for_multiple_lines_and_vendors(self):
        vendor = self.partner_vendor_service.copy({'name': 'Second license vendor'})
        self.service_purchase_2.seller_ids.partner_id = vendor
        order = self._order([self.service_purchase_1, self.service_purchase_2, self.service_purchase_1])
        self.assertTrue(order.action_confirm())
        self._assert_notice(order)
        self.assertEqual(len(order.order_line.purchase_line_ids.order_id), 2)

    def test_batch_sales_are_independent(self):
        first = self._order()
        second = self._order([self.non_recurring])
        third = self._order()
        (first | second | third).action_confirm()
        self._assert_notice(first)
        self.assertFalse(self._mails(second))
        self._assert_notice(third)

    def test_draft_reuse_with_old_and_new_lines(self):
        order = self._order([self.service_purchase_1, self.service_purchase_2])
        previous = order.order_line[:1].sudo()._purchase_service_create()[order.order_line[:1]]
        order.action_confirm()
        self._assert_notice(order)
        self.assertEqual(order.order_line.purchase_line_ids.order_id, previous.order_id)
        self.assertEqual(len(order.order_line.purchase_line_ids), 2)

    def test_preexisting_lines_do_not_notify(self):
        order = self._order()
        order.order_line.sudo()._purchase_service_create()
        order.action_confirm()
        self.assertFalse(self._mails(order))

    def test_previous_recurring_plus_new_one_off_does_not_notify(self):
        order = self._order([self.service_purchase_1, self.non_recurring])
        order.order_line[:1].sudo()._purchase_service_create()
        order.action_confirm()
        self.assertFalse(self._mails(order))

    def test_reconfirmation_and_quantity_change_do_not_duplicate(self):
        order = self._order()
        order.action_confirm()
        initial_mail = self._assert_notice(order)
        order.order_line.product_uom_qty = 5
        self.assertEqual(self._mails(order), initial_mail)
        order._action_cancel()
        order.action_draft()
        order.action_confirm()
        self.assertEqual(self._mails(order), initial_mail)

    def test_later_quantity_creating_purchase_line_does_not_notify(self):
        order = self._order()
        order.action_confirm()
        initial_mail = self._assert_notice(order)
        initial_lines = order.order_line.purchase_line_ids
        initial_lines.order_id.button_confirm()
        order.order_line.product_uom_qty = 5
        self.assertGreater(len(order.order_line.purchase_line_ids), len(initial_lines))
        self.assertEqual(self._mails(order), initial_mail)

    def test_multiple_companies_have_their_own_recipient(self):
        other_company = self.setup_other_company()['company']
        other_recipient = self.recipient.copy({'name': 'Other company recipient', 'email': 'other@example.invalid'})
        other_company.notify_purchase_license_id = other_recipient
        self.service_purchase_1.seller_ids.company_id = False
        self.service_purchase_1.with_company(other_company).service_to_purchase = True
        first = self._order()
        second = self._order(company=other_company)
        self.assertTrue(second.order_line)
        self.assertEqual(second.order_line.product_id, self.service_purchase_1)
        (first | second).with_context(
            allowed_company_ids=(self.env.company | other_company).ids,
        ).action_confirm()
        self.assertTrue(second.sudo().order_line.purchase_line_ids)
        self._assert_notice(first)
        self._assert_notice(second, other_recipient)
        self.assertEqual(second.order_line.purchase_line_ids.company_id, other_company)

    def test_salesperson_without_purchase_permissions(self):
        user = new_test_user(self.env, login='license_notice_salesperson',
                             groups='sales_team.group_sale_salesman',
                             company_id=self.env.company.id,
                             company_ids=[Command.set([self.env.company.id])])
        order = self._order()
        order.user_id = user
        self.assertFalse(self.env['purchase.order'].with_user(user).has_access('read'))
        order.with_user(user).action_confirm()
        self._assert_notice(order)

    def test_missing_recipient_is_internal_note(self):
        self.env.company.notify_purchase_license_id = False
        order = self._order()
        order.action_confirm()
        self._assert_informative_failure(order, 'recipient is missing')

    @mute_logger('odoo.addons.miac_sale_purchase_notification.models.sale_order')
    def test_inaccessible_recipient_preserves_sale_without_elevating_contacts(self):
        other_company = self.setup_other_company()['company']
        private_recipient = self.env['res.partner'].with_company(other_company).create({
            'name': 'Private license recipient', 'email': 'private@example.invalid',
            'company_id': other_company.id,
        })
        self.env.company.notify_purchase_license_id = private_recipient
        user = new_test_user(self.env, login='license_notice_restricted_salesperson',
                             groups='sales_team.group_sale_salesman',
                             company_id=self.env.company.id,
                             company_ids=[Command.set([self.env.company.id])])
        order = self._order()
        order.user_id = user
        self.assertFalse(private_recipient.with_user(user).with_context(
            allowed_company_ids=[self.env.company.id]).has_access('read'))
        order.with_user(user).action_confirm()
        self._assert_informative_failure(order, 'could not be generated')

    def test_missing_invalid_or_multiple_email_is_internal_note(self):
        for email in (False, 'invalid address', 'one@example.invalid, two@example.invalid'):
            self.recipient.email = email
            order = self._order()
            order.action_confirm()
            self._assert_informative_failure(order, 'recipient is missing')

    def test_missing_template_is_internal_note(self):
        self.template.unlink()
        order = self._order()
        order.action_confirm()
        self._assert_informative_failure(order, 'template is missing')

    @mute_logger('odoo.addons.miac_sale_purchase_notification.models.sale_order', 'odoo.addons.mail.models.mail_render_mixin')
    def test_broken_template_preserves_confirmation_and_purchases(self):
        self.template.subject = '{{ object.missing_license_notice_attribute }}'
        order = self._order()
        order.action_confirm()
        self._assert_informative_failure(order, 'could not be generated')

    @mute_logger('odoo.addons.miac_sale_purchase_notification.models.sale_order')
    def test_partial_mail_creation_is_rolled_back(self):
        order = self._order()
        def fail_after_creation(template, res_id, **kwargs):
            template.env['mail.mail'].sudo().create({
                'subject': 'Partial license mail must disappear',
                'body_html': '<p>Partial attempt</p>',
                'email_from': 'sender@example.invalid',
                'email_to': 'recipient@example.invalid',
            })
            raise UserError('Simulated failure after mail creation')
        with patch.object(type(self.template), 'send_mail', fail_after_creation):
            order.action_confirm()
        self._assert_informative_failure(order, 'could not be generated')
        self.assertFalse(self.env['mail.mail'].sudo().search([
            ('subject', '=', 'Partial license mail must disappear')]))

    @mute_logger('odoo.addons.miac_sale_purchase_notification.models.sale_order')
    def test_one_failed_notice_does_not_stop_next_sale(self):
        first, second = self._order(), self._order()
        original_send_mail = type(self.template).send_mail
        def fail_first(template, res_id, **kwargs):
            if res_id == first.id:
                raise UserError('Simulated failure for the first sale')
            return original_send_mail(template, res_id, **kwargs)
        with patch.object(type(self.template), 'send_mail', fail_first):
            (first | second).action_confirm()
        self._assert_informative_failure(first, 'could not be generated')
        self._assert_notice(second)

    def test_legacy_and_custom_template_preserves_content_and_restricts_recipients(self):
        extra = self.recipient.copy({'email': 'extra@example.invalid'})
        values = {
            'partner_to': '${object.company_id.notify_purchase_license_id.id}',
            'email_to': 'unwanted@example.invalid', 'email_cc': 'cc@example.invalid',
            'body_html': '<p>Contenido personalizado conservado.</p>',
            'subject': 'Aviso personalizado',
        }
        self.template.write(values)
        # Even a translated, customized template that resolves other partners is restricted.
        self.template.partner_to = str(extra.id)
        order = self._order()
        order.action_confirm()
        mail = self._assert_notice(order)
        self.assertIn('Contenido personalizado conservado', mail.body_html)
        self.assertEqual(self.template.partner_to, str(extra.id))
        self.template.partner_to = values['partner_to']
        second = self._order()
        second.action_confirm()
        self._assert_notice(second)
        self.assertEqual(self.template.partner_to, values['partner_to'])
        self.assertEqual(self.template.email_to, values['email_to'])
        self.assertEqual(self.template.email_cc, values['email_cc'])

    def test_recipient_greeting_language_and_salesperson_signature(self):
        self.env['res.lang']._activate_lang('es_ES')
        self.recipient.lang = 'es_ES'
        self.env.user.signature = '<p>Firma del comercial MIAC</p>'
        order = self._order()
        order.action_confirm()
        mail = self._assert_notice(order)
        self.assertIn('Compra de Licencias', mail.subject)
        self.assertIn('Hola', mail.body_html)
        self.assertIn(self.recipient.name, mail.body_html)
        self.assertIn('se ha generado una compra de licencias', mail.body_html)
        self.assertIn('Firma del comercial MIAC', mail.body_html)
        self.assertIn(order.name, mail.body_html)

    def test_native_confirmation_failure_does_not_notify(self):
        order = self._order()
        self.service_purchase_1.seller_ids.unlink()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            order.action_confirm()
        self.assertEqual(order.state, 'draft')
        self.assertFalse(self._mails(order))

    def test_company_form_and_template_preservation_metadata(self):
        with Form(self.env.company) as form:
            self.assertFalse(form._get_modifier('notify_purchase_license_id', 'invisible'))
            self.assertEqual(form.notify_purchase_license_id, self.recipient)
        data = self.env['ir.model.data'].search([
            ('module', '=', 'miac_sale_purchase_notification'),
            ('name', '=', 'email_template_sale_purchase_license'),
        ])
        self.assertTrue(data.noupdate)
