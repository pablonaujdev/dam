from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


@tagged('post_install', '-at_install', 'jh_migration19')
class TestJhMigration19(TestSubscriptionCommon):
    """Functional regressions to run only in the authorized isolated Odoo 19 DB."""

    def _jh_order(self, recurring=True):
        product = self.product if recurring else self.product2.copy({'recurring_invoice': False})
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_month.id if recurring else False,
            'order_line': [Command.create({'product_id': product.id,
                'product_uom_qty': 1, 'price_unit': 37, 'discount': 7})],
        })
        return order

    def test_negotiated_price_discount_quantity_confirmation_invoice(self):
        order = self._jh_order(recurring=False)
        line = order.order_line
        line.write({'product_uom_qty': 3})
        self.assertEqual((line.price_unit, line.discount), (37, 7))
        order.action_confirm()
        self.assertEqual((line.price_unit, line.discount), (37, 7))
        invoice = order._create_invoices()
        invoice_line = invoice.invoice_line_ids.filtered(lambda item: item.product_id == line.product_id)
        self.assertEqual((invoice_line.price_unit, invoice_line.discount), (37, 7))

    def test_explicit_zero_price_and_discount(self):
        order = self._jh_order(recurring=False)
        line = self.env['sale.order.line'].create({
            'order_id': order.id, 'product_id': order.order_line.product_id.id,
            'price_unit': 0, 'discount': 0, 'product_uom_qty': 1})
        line.write({'product_uom_qty': 5})
        self.assertEqual((line.price_unit, line.discount), (0, 0))

    def test_repeated_products_renewal_lots_conditions(self):
        order = self._jh_order()
        lots = self.env['stock.lot'].create([
            {'name': 'JH-MIAC-A', 'product_id': self.product.id},
            {'name': 'JH-MIAC-B', 'product_id': self.product.id},
        ])
        order.order_line.lot_id = lots[0]
        self.env['sale.order.line'].create({'order_id': order.id,
            'product_id': self.product.id, 'price_unit': 63, 'discount': 11,
            'product_uom_qty': 2, 'lot_id': lots[1].id})
        order.action_confirm()
        values = order.with_context(renewal_pricing_mode='keep_current')._prepare_upsell_renew_order_values('2_renewal')
        renewal = self.env['sale.order'].create(values)
        for line in renewal.order_line.filtered('product_id'):
            self.assertEqual(line.lot_id, line.parent_line_id.lot_id)
            self.assertEqual((line.price_unit, line.discount), (line.parent_line_id.price_unit, line.parent_line_id.discount))

    def test_renewal_update_tariff_and_native_duplicate_rejection(self):
        order = self._jh_order()
        order.action_confirm()
        order._create_invoices().action_post()
        values = order.with_context(renewal_pricing_mode='update_tariff')._prepare_upsell_renew_order_values('2_renewal')
        renewal = self.env['sale.order'].create(values)
        for line in renewal.order_line.filtered('product_id'):
            expected = line._get_pricelist_reprice_vals()
            self.assertAlmostEqual(line.price_unit, expected['price_unit'])
            self.assertAlmostEqual(line.discount, expected['discount'])
        second = self.env['sale.order'].create(values)
        renewal.action_confirm()
        with self.assertRaises(UserError), self.cr.savepoint():
            second.action_confirm()

    def test_commission_manual_category_agent_and_invoice(self):
        default, category, manual = self.env['commission'].create([
            {'name': 'JH agent', 'commission_type': 'fixed', 'fix_qty': 5},
            {'name': 'JH category', 'commission_type': 'fixed', 'fix_qty': 10},
            {'name': 'JH manual', 'commission_type': 'fixed', 'fix_qty': 15},
        ])
        agent = self.env['res.partner'].create({'name': 'JH agent', 'agent': True, 'commission_id': default.id})
        self.partner.commission_agent_ids = [Command.set(agent.ids)]
        order = self._jh_order(recurring=False)
        line = order.order_line
        self.assertEqual(line.agent_ids.commission_id, default)
        line.product_id.categ_id = self.env['product.category'].create({'name': 'JH category'})
        rule = self.env['product.category.agent.commission'].create({
            'categ_id': line.product_id.categ_id.id, 'agent_id': agent.id, 'commission_id': category.id})
        line.recompute_agents()
        self.assertEqual(line.agent_ids.commission_id, category)
        self.assertFalse(line.agent_ids.z_commission_manual)
        line.agent_ids.write({'commission_id': manual.id})
        rule.commission_id = default
        line.product_uom_qty = 3
        self.assertEqual(line.agent_ids.commission_id, manual)
        order.action_confirm()
        invoice = order._create_invoices()
        self.assertEqual(invoice.invoice_line_ids.filtered('product_id').agent_ids.commission_id, manual)

    def test_native_status_recompute_does_not_change_quantities_period(self):
        order = self._jh_order()
        order.action_confirm()
        lines = order.order_line
        before = (lines.mapped('product_uom_qty'), lines.mapped('qty_to_invoice'), order.next_invoice_date)
        self.env['sale.order']._cron_recalcular_invoice_status()
        self.assertEqual(before, (lines.mapped('product_uom_qty'), lines.mapped('qty_to_invoice'), order.next_invoice_date))

    def test_renewal_cron_and_notices_idempotent(self):
        order = self._jh_order()
        order.action_confirm()
        order.end_date = fields.Date.today() + timedelta(days=30)
        self.env['jh.sales.subscription.advice'].create({
            'name': self.env.user.id, 'jh_company_id': order.company_id.id, 'jh_notify_type': 'activity'})
        advice = self.env['jh.sales.subscription.advice']
        advice.renovation_subscriptons_advice_cron()
        count = self.env['jh.subscription.renewal.notification'].search_count([('jh_order_id', '=', order.id)])
        advice.renovation_subscriptons_advice_cron()
        self.assertEqual(count, 1)
        self.assertEqual(self.env['jh.subscription.renewal.notification'].search_count([('jh_order_id', '=', order.id)]), count)
        self.env['sale.order'].renovation_subscriptons_cron()
        renewal = order.order_renove
        self.assertTrue(renewal)
        self.env['sale.order'].renovation_subscriptons_cron()
        self.assertEqual(order.order_renove, renewal)

    def test_report_query_and_exports(self):
        order = self._jh_order(recurring=False)
        order.action_confirm()
        invoice = order._create_invoices()
        invoice.invoice_date = fields.Date.today()
        invoice.action_post()
        records = self.env['account.invoice.report'].search([('move_id', '=', invoice.id)])
        self.assertTrue(records)
        self.assertAlmostEqual(sum(records.mapped('price_subtotal')), invoice.amount_untaxed)
        wizard = self.env['jh.invoice.report.wizard'].create({'date_from': invoice.invoice_date, 'date_to': invoice.invoice_date})
        fields_dict = wizard._get_selected_fields()
        data = wizard._prepare_data(records, fields_dict)
        self.assertTrue(wizard._export_xlsx(data, fields_dict))
        self.assertTrue(wizard._export_csv(data, fields_dict))

    def test_automatic_history_read_preserves_manual_attachment(self):
        manual = self.env['jh.client.sheet.manual'].create({'parent_id': self.partner.id, 'jh_account_move': 'LEGACY-FV-001'})
        attachment = self.env['ir.attachment'].create({'name': 'original.pdf', 'type': 'binary',
            'datas': 'JVBERi0xLjQK', 'res_model': manual._name, 'res_id': manual.id})
        self.partner.jh_client_sheet_ids.read(['jh_account_move', 'jh_quantity_sold'])
        self.partner.invalidate_recordset(['jh_client_sheet_ids'])
        self.partner.jh_client_sheet_ids.read(['jh_account_move', 'jh_quantity_sold'])
        self.assertTrue(manual.exists())
        self.assertEqual((attachment.res_model, attachment.res_id), (manual._name, manual.id))
