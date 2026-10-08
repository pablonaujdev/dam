from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


@tagged('post_install', '-at_install')
class TestSubscriptionPrebilling(TestSubscriptionCommon):
    """Flujo nativo V19, sin depender de IDs de pedidos de producción."""

    def _create_future_subscription(self, product=None, start=None, end=None):
        start = start or fields.Date.today() + relativedelta(days=10)
        end = end or start + relativedelta(years=1)
        order = self.env['sale.order'].create({
            'partner_id': self.subscription.partner_id.id,
            'pricelist_id': self.subscription.pricelist_id.id,
            'plan_id': self.plan_year.id,
            'start_date': start,
            'end_date': end,
            'order_line': [Command.create({
                'product_id': (product or self.product).id,
                'product_uom_qty': 1,
                'price_unit': 685,
                'discount': 0,
            })],
        })
        order.action_confirm()
        self.assertEqual(order.state, 'sale')
        return order

    def _invoice(self, order):
        wizard = self.env['sale.advance.payment.inv'].create({
            'sale_order_ids': [Command.set(order.ids)],
            'advance_payment_method': 'delivered',
        })
        wizard.create_invoices()
        return order.order_line.invoice_lines.move_id.filtered(lambda move: move.state == 'draft')

    def _recompute(self, order):
        lines = order.order_line
        for name in ('last_invoiced_date', 'qty_invoiced', 'qty_to_invoice', 'invoice_status'):
            self.env.add_to_compute(lines._fields[name], lines)
            lines._recompute_recordset([name])
        self.env.add_to_compute(order._fields['invoice_status'], order)
        order._recompute_recordset(['invoice_status'])

    def _post_invoice(self, order):
        invoice = self._invoice(order)
        self.assertEqual(len(invoice), 1)
        invoice.invoice_date = fields.Date.today()
        invoice.action_post()
        self._recompute(order)
        return invoice

    def test_future_prepaid_pending_and_automatic_date_guard(self):
        order = self._create_future_subscription()
        self.assertEqual(order.order_line.qty_delivered, 0)
        self.assertEqual(order.order_line.invoice_status, 'to invoice')
        self.assertEqual(order.invoice_status, 'to invoice')
        self.assertFalse(order.with_context(recurring_automatic=True)._get_invoiceable_lines())

    def test_prepaid_invoice_period_and_no_extra_invoice(self):
        order = self._create_future_subscription()
        start, end = order.start_date, order.end_date
        invoice = self._post_invoice(order)
        self.assertEqual(invoice.amount_untaxed, 685)
        line = invoice.invoice_line_ids.filtered(lambda line: line.product_id == self.product)
        self.assertEqual(line.deferred_start_date, start)
        self.assertEqual(line.deferred_end_date, end - relativedelta(days=1))
        self.assertEqual(order.start_date, start)
        self.assertEqual(order.end_date, end)
        self.assertEqual(order.next_invoice_date, end)
        self.assertEqual(order.order_line.last_invoiced_date, end - relativedelta(days=1))
        self.assertEqual(order.order_line.invoice_status, 'invoiced')
        self.assertEqual(order.invoice_status, 'invoiced')
        self.assertFalse(order._get_invoiceable_lines())
        with self.assertRaises(UserError), self.cr.savepoint():
            self._invoice(order)

    def test_draft_is_not_posted_coverage_and_no_second_draft(self):
        order = self._create_future_subscription()
        self._invoice(order)
        self.assertFalse(order.order_line._jh_has_posted_invoice_coverage(2))
        self.assertNotEqual(order.invoice_status, 'invoiced')
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._invoice(order)

    def test_canceled_draft_becomes_pending(self):
        order = self._create_future_subscription()
        self._invoice(order).button_cancel()
        self._recompute(order)
        self.assertEqual(order.order_line.invoice_status, 'to invoice')
        self.assertEqual(order.invoice_status, 'to invoice')

    def test_full_refund_is_not_covered(self):
        order = self._create_future_subscription()
        invoice = self._post_invoice(order)
        refund = invoice._reverse_moves(default_values_list=[{'invoice_date': fields.Date.today()}])
        refund.action_post()
        self._recompute(order)
        self.assertFalse(order.order_line._jh_has_posted_invoice_coverage(2))
        self.assertNotEqual(order.order_line.invoice_status, 'invoiced')
        self.assertNotEqual(order.invoice_status, 'invoiced')

    def test_partial_refund_is_not_full_coverage(self):
        order = self._create_future_subscription()
        invoice = self._post_invoice(order)
        refund = invoice._reverse_moves(default_values_list=[{'invoice_date': fields.Date.today()}])
        refund.invoice_line_ids.filtered('product_id').quantity = 0.5
        refund.action_post()
        self._recompute(order)
        self.assertFalse(order.order_line._jh_has_posted_invoice_coverage(2))
        self.assertNotEqual(order.invoice_status, 'invoiced')

    def test_postpaid_service_without_delivery_remains_no(self):
        service = self.product.copy({'name': 'Servicio postpago', 'invoice_policy': 'delivery'})
        order = self._create_future_subscription(product=service)
        self.assertTrue(order.order_line._is_postpaid_line())
        self.assertEqual(order.order_line.qty_delivered, 0)
        self.assertEqual(order.order_line.invoice_status, 'no')
        self.assertEqual(order.invoice_status, 'no')

    def test_free_subscription_remains_no(self):
        order = self._create_future_subscription()
        order.order_line.discount = 100
        self.assertEqual(order.invoice_status, 'no')

    def test_invalid_end_date_is_rejected(self):
        start = fields.Date.today() + relativedelta(days=10)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._create_future_subscription(start=start, end=start - relativedelta(days=1))

    def test_native_renewal_is_pending_before_start(self):
        future_start = fields.Date.today() + relativedelta(days=10)
        parent = self._create_future_subscription(start=future_start - relativedelta(years=1))
        self._post_invoice(parent)
        action = parent.with_context(
            skip_renewal_price_confirmation=True, renewal_pricing_mode='keep_current',
        ).prepare_renewal_order()
        renewal = self.env['sale.order'].browse(action['res_id'])
        renewal.end_date = future_start + relativedelta(years=1)
        renewal.action_confirm()
        self.assertEqual(parent.subscription_state, '5_renewed')
        self.assertEqual(renewal.start_date, future_start)
        self.assertEqual(renewal.order_line.invoice_status, 'to invoice')
        self.assertEqual(renewal.invoice_status, 'to invoice')

    def test_start_date_arrives_and_pending_is_preserved(self):
        order = self._create_future_subscription()
        with patch.object(fields.Date, 'today', return_value=order.start_date):
            self._recompute(order)
            self.assertEqual(order.invoice_status, 'to invoice')

    def test_invoice_before_contract_start_is_not_coverage(self):
        future_start = fields.Date.today() + relativedelta(days=10)
        order = self._create_future_subscription(start=future_start - relativedelta(years=1))
        self._post_invoice(order)
        order.write({'start_date': future_start, 'end_date': future_start + relativedelta(years=1)})
        self._recompute(order)
        self.assertFalse(order.order_line._jh_has_posted_invoice_coverage(2))
        self.assertNotEqual(order.invoice_status, 'invoiced')

    def test_scoped_recompute_is_idempotent_and_preserves_quantities(self):
        order = self._create_future_subscription()
        before = (order.start_date, order.end_date, order.next_invoice_date,
                  order.order_line.product_uom_qty, order.order_line.qty_delivered,
                  order.order_line.qty_invoiced, order.order_line.price_unit)
        model = self.env['sale.order'].with_context(cron_id=False)
        model._cron_recalcular_invoice_status(only_active_subscriptions=True)
        result = model._cron_recalcular_invoice_status(only_active_subscriptions=True)
        self.assertEqual(result['orders_changed'], 0)
        self.assertEqual(result['lines_changed'], 0)
        after = (order.start_date, order.end_date, order.next_invoice_date,
                 order.order_line.product_uom_qty, order.order_line.qty_delivered,
                 order.order_line.qty_invoiced, order.order_line.price_unit)
        self.assertEqual(before, after)
