"""The shortcut delegates eligibility and accounting to native purchase flows."""
import ast

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged('post_install', '-at_install', 'miac_purchase_invoice19')
class TestMiacPurchaseInvoice19(AccountTestInvoicingCommon):
    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups() | cls.quick_ref('purchase.group_purchase_manager')
        stock_group = cls.env.ref('stock.group_stock_manager', raise_if_not_found=False)
        return groups | stock_group if stock_group else groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.product = cls.env['product.product'].create({'name': 'PURCHASE-INVOICE19 Ordered service',
            'type': 'service', 'purchase_method': 'purchase', 'categ_id': cls.product_category.id})
        cls.received_product = cls.env['product.product'].create({'name': 'PURCHASE-INVOICE19 Received goods',
            'type': 'consu', 'purchase_method': 'receive', 'categ_id': cls.product_category.id})
        cls.action = cls.env.ref('miac_purchase_to_invoice.purchase_to_invoice_action')

    def purchase(self, product=None, company=None):
        model = self.env['purchase.order'].with_company(company or self.env.company)
        return model.create({'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': (product or self.product).id,
                'product_qty': 4, 'price_unit': 80, 'tax_ids': [Command.clear()],
                'date_planned': fields.Datetime.now()})]})

    def visible(self, order, user=None, extra_domain=None):
        model = self.env['purchase.order']
        if user:
            model = model.with_user(user)
        domain = ast.literal_eval(self.action.domain) + [('id', '=', order.id)] + (extra_domain or [])
        return bool(model.search(domain))

    def bill(self, order, quantity):
        return self.env['account.move'].create({**order._prepare_invoice(),
            'invoice_date': fields.Date.today(), 'invoice_line_ids': [Command.create({
                **order.order_line._prepare_account_move_line(), 'quantity': quantity})]})

    def test_action_menu_translation_and_native_views(self):
        self.assertEqual(self.action.res_model, 'purchase.order')
        self.assertEqual(self.action.view_mode, 'list,form')
        self.assertEqual(ast.literal_eval(self.action.domain), [('invoice_status', '=', 'to invoice')])
        menu = self.env.ref('miac_purchase_to_invoice.menu_purchase_to_invoice')
        self.assertEqual(menu.parent_id, self.env.ref('purchase.menu_purchase_root'))
        self.assertEqual(menu.sequence, 2)
        self.assertEqual(menu.action, self.action)
        self.assertEqual(self.action.with_context(lang='es_ES').name, 'Pedidos a Facturar')
        self.assertEqual(menu.with_context(lang='es_ES').name, 'Pedidos a Facturar')
        for view_type in ('list', 'form', 'search'):
            self.assertTrue(self.env['purchase.order'].get_view(view_type=view_type)['arch'])

    def test_drafts_cancellation_and_mandatory_domain(self):
        order = self.purchase()
        self.assertFalse(self.visible(order))
        amounts = order.amount_untaxed, order.amount_tax, order.amount_total
        order.button_confirm()
        self.assertTrue(self.visible(order))
        self.assertTrue(self.visible(order, extra_domain=[('partner_id', '=', self.partner_a.id)]))
        self.assertFalse(self.visible(order, extra_domain=[('state', '=', 'draft')]))
        self.assertEqual(amounts, (order.amount_untaxed, order.amount_tax, order.amount_total))
        order.button_cancel()
        self.assertFalse(self.visible(order))
        self.assertEqual(self.action.domain, "[('invoice_status', '=', 'to invoice')]")

    def test_partial_and_full_draft_bills_and_cancellation(self):
        order = self.purchase()
        order.button_confirm()
        bill = self.bill(order, 1.5)
        self.assertEqual(bill.state, 'draft')
        self.assertEqual(order.order_line.qty_to_invoice, 2.5)
        self.assertTrue(self.visible(order))
        bill.invoice_line_ids.quantity = 4
        self.assertEqual(order.invoice_status, 'invoiced')
        self.assertFalse(self.visible(order))
        bill.button_cancel()
        self.assertEqual(order.order_line.qty_to_invoice, 4)
        self.assertTrue(self.visible(order))

    def test_receipt_policy_and_partial_received_quantities(self):
        order = self.purchase(self.received_product)
        order.button_confirm()
        self.assertFalse(self.visible(order))
        def receive(quantity):
            if 'picking_ids' not in order._fields:
                order.order_line.qty_received = order.order_line.qty_received + quantity
                return
            picking = order.picking_ids.filtered(lambda record: record.state not in ('done', 'cancel'))
            self.assertEqual(len(picking), 1)
            picking.move_ids.quantity = quantity
            action = picking.button_validate()
            if isinstance(action, dict):
                self.assertEqual(action['res_model'], 'stock.backorder.confirmation')
                self.env[action['res_model']].with_context(action['context']).create({}).process()
            self.assertEqual(picking.state, 'done')
        receive(2)
        self.assertTrue(self.visible(order))
        bill = self.bill(order, 1)
        self.assertEqual(order.order_line.qty_to_invoice, 1)
        self.assertTrue(self.visible(order))
        bill.invoice_line_ids.quantity = 2
        self.assertFalse(self.visible(order))
        receive(1)
        self.assertTrue(self.visible(order))

    def test_refund_and_negative_pending_quantities(self):
        order = self.purchase()
        order.button_confirm()
        bill = self.bill(order, 4)
        bill.action_post()
        self.assertFalse(self.visible(order))
        refund = bill._reverse_moves(default_values_list=[{'invoice_date': fields.Date.today()}])
        self.assertEqual(refund.state, 'draft')
        self.assertEqual(order.order_line.qty_to_invoice, 4)
        self.assertTrue(self.visible(order))
        refund.button_cancel()
        self.assertFalse(self.visible(order))
        self.bill(order, 1)
        self.assertEqual(order.order_line.qty_to_invoice, -1)
        self.assertTrue(self.visible(order))

    def test_purchase_users_and_company_rules(self):
        user = self.env['res.users'].create({'name': 'PURCHASE-INVOICE19 Buyer',
            'login': 'purchase-invoice19-buyer', 'company_id': self.env.company.id,
            'company_ids': [Command.set(self.env.company.ids)],
            'group_ids': [Command.set(self.env.ref('purchase.group_purchase_user').ids)]})
        order = self.purchase()
        order.button_confirm()
        self.assertTrue(self.visible(order, user=user))
        other = self.setup_other_company()['company']
        foreign = self.purchase(company=other)
        foreign.button_confirm()
        self.assertFalse(self.visible(foreign, user=user))
        reader = self.env['res.users'].create({'name': 'PURCHASE-INVOICE19 No purchase access',
            'login': 'purchase-invoice19-no-access',
            'group_ids': [Command.set(self.env.ref('base.group_user').ids)]})
        with self.assertRaises(AccessError):
            self.visible(order, user=reader)
