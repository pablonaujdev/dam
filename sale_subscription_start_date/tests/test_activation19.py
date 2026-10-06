from datetime import date, datetime, timedelta
from unittest.mock import patch

from freezegun import freeze_time
from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import Form, new_test_user, tagged
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


@tagged('post_install', '-at_install', 'subscription_activation19')
class TestSubscriptionActivation19(TestSubscriptionCommon):
    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.quick_ref('stock.group_stock_manager')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env['product.product'].create({
            'name': 'Activation recurring service', 'type': 'service',
            'recurring_invoice': True, 'invoice_policy': 'order',
            'subscription_rule_ids': [Command.create({'plan_id': cls.plan_month.id, 'fixed_price': 100})],
        })
        cls.goods = cls.env['product.product'].create({
            'name': 'Activation delivery', 'type': 'consu', 'days_to_activate': 3,
            'invoice_policy': 'order', 'list_price': 10,
        })
        cls.goods_later = cls.env['product.product'].create({
            'name': 'Activation delivery later', 'type': 'consu', 'days_to_activate': 7,
            'invoice_policy': 'order', 'list_price': 10,
        })
        cls.planned = datetime(2026, 1, 30, 12)
        cls.env.company.resource_calendar_id.tz = 'UTC'

    def _order(self, quantity=1, confirm=True, **extra):
        values = {'partner_id': self.partner.id, 'plan_id': self.plan_month.id,
                  'start_date': date(2026, 1, 1), 'next_invoice_date': date(2026, 1, 1),
                  'end_date': date(2027, 1, 1),
                  'order_line': [Command.create({'product_id': self.service.id, 'product_uom_qty': 1}),
                                 Command.create({'product_id': self.goods.id, 'product_uom_qty': quantity})]}
        values.update(extra)
        order = self.env['sale.order'].create(values)
        if confirm:
            order.action_confirm()
        return order

    def _prepare(self, picking, planned=None):
        picking.scheduled_date = planned or self.planned
        for move in picking.move_ids.filtered(lambda item: item.state != 'cancel'):
            move.write({'quantity': move.product_uom_qty, 'picked': True})

    def _finish(self, picking, planned=None):
        self._prepare(picking, planned)
        with freeze_time('2026-02-10 12:00:00'):
            result = picking.button_validate()
        self.assertEqual(picking.state, 'done')
        return result

    def _dates(self, order):
        return order.start_date, order.next_invoice_date, order.end_date

    def _extra_delivery(self, order, code='outgoing', **extra):
        original = order.picking_ids[:1] or order.subscription_id.picking_ids[:1]
        picking_type = original.picking_type_id
        source, target = original.location_id, original.location_dest_id
        if code == 'incoming':
            picking_type = order.warehouse_id.in_type_id
            source, target = target, source
        elif code == 'internal':
            picking_type = order.warehouse_id.int_type_id
            target = source
        values = {'picking_type_id': picking_type.id, 'location_id': source.id,
                  'location_dest_id': target.id, 'partner_id': self.partner.id,
                  'move_ids': [Command.create({'product_id': self.goods.id,
                      'product_uom_qty': 1, 'product_uom': self.goods.uom_id.id,
                      'location_id': source.id, 'location_dest_id': target.id,
                      'sale_line_id': order.order_line.filtered(lambda line: line.product_id == self.goods).id})]}
        values.update(extra)
        picking = self.env['stock.picking'].create(values)
        picking.action_confirm()
        return picking

    def test_product_batch_category_explicit_and_archived(self):
        category = self.env['product.category'].create({'name': 'Activation category', 'days_to_activate': 8})
        first, manual = self.env['product.template'].create([
            {'name': 'Activation automatic', 'categ_id': category.id},
            {'name': 'Activation explicit', 'categ_id': category.id, 'days_to_activate': 0},
        ])
        self.assertEqual((first.days_to_activate, manual.days_to_activate), (8, 0))
        manual.active = False
        category.days_to_activate = 9
        self.assertEqual((first.days_to_activate, manual.days_to_activate), (9, 9))
        other = self.env['product.category'].create({'name': 'Activation other', 'days_to_activate': 4})
        first.categ_id = other
        self.assertEqual(first.days_to_activate, 4)
        first.write({'categ_id': category.id, 'days_to_activate': 2})
        self.assertEqual(first.days_to_activate, 2)
        with Form(first) as form:
            form.categ_id = other
            self.assertEqual(form.days_to_activate, 4)
        default = self.env['product.template'].with_context(default_days_to_activate=0).create({'name': 'Explicit context'})
        self.assertEqual(default.days_to_activate, 0)

    def test_completed_delivery_uses_planned_date_and_preserves_line_dates(self):
        order = self._order()
        line = order.order_line.filtered('recurring_invoice')
        manual = self.env['sale.order.line'].create({'order_id': order.id, 'product_id': self.service.id,
            'date_subs_start': date(2026, 3, 1), 'date_subs_end': date(2026, 7, 1)})
        self._finish(order.picking_ids)
        expected = date(2026, 2, 2)
        self.assertEqual(self._dates(order), (expected, expected, date(2026, 3, 2)))
        self.assertEqual((line.date_subs_start, line.date_subs_end), (expected, date(2026, 3, 2)))
        self.assertEqual((manual.date_subs_start, manual.date_subs_end), (date(2026, 3, 1), date(2026, 7, 1)))
        messages = order.message_ids.ids
        order.picking_ids._action_done()
        self.assertEqual(order.message_ids.ids, messages)

    def test_backorder_wizard_and_each_partial_delivery(self):
        order = self._order(quantity=2)
        picking = order.picking_ids
        picking.scheduled_date = self.planned
        picking.move_ids.write({'quantity': 1, 'picked': True})
        before = self._dates(order)
        action = picking.button_validate()
        self.assertEqual(action['res_model'], 'stock.backorder.confirmation')
        self.assertEqual(self._dates(order), before)
        wizard = self.env['stock.backorder.confirmation'].with_context(action['context']).create({
            'pick_ids': [Command.set(picking.ids)]})
        wizard.process()
        self.assertEqual(order.start_date, date(2026, 2, 2))
        backorder = picking.backorder_ids
        self._finish(backorder, datetime(2026, 2, 15, 12))
        self.assertEqual(self._dates(order), (date(2026, 2, 18), date(2026, 2, 18), date(2026, 3, 18)))

    def test_maximum_only_from_completed_positive_moves(self):
        order = self._order(confirm=False)
        self.env['sale.order.line'].create({'order_id': order.id, 'product_id': self.goods_later.id,
                                          'name': self.goods_later.display_name, 'product_uom_qty': 1})
        order.action_confirm()
        self._finish(order.picking_ids)
        self.assertEqual(order.start_date, date(2026, 2, 6))
        second = self._order(confirm=False)
        self.env['sale.order.line'].create({'order_id': second.id, 'product_id': self.goods_later.id,
                                          'name': self.goods_later.display_name, 'product_uom_qty': 1})
        second.action_confirm()
        second.picking_ids.move_ids.filtered(lambda move: move.product_id == self.goods_later)._action_cancel()
        self._finish(second.picking_ids)
        self.assertEqual(second.start_date, date(2026, 2, 2))

    def test_timezone_and_billing_periods(self):
        self.env.company.resource_calendar_id.tz = 'America/Bogota'
        self.env.user.tz = 'Asia/Tokyo'
        self.goods.days_to_activate = 0
        for plan, end in [(self.plan_week, date(2026, 2, 7)),
                          (self.plan_month, date(2026, 2, 28)),
                          (self.plan_year, date(2027, 1, 31))]:
            order = self._order(plan_id=plan.id)
            self._finish(order.picking_ids, datetime(2026, 2, 1, 2))
            self.assertEqual(self._dates(order), (date(2026, 1, 31), date(2026, 1, 31), end))

    def test_multiple_deliveries_ordered_by_planned_date(self):
        order = self._order()
        first = order.picking_ids
        second = self._extra_delivery(order)
        self._prepare(first, datetime(2026, 2, 20, 12))
        self._prepare(second, datetime(2026, 2, 10, 12))
        (first | second)._action_done()
        self.assertEqual(order.start_date, date(2026, 2, 23))

    def test_returns_internal_and_closed_contracts_are_excluded(self):
        order = self._order()
        before = self._dates(order)
        self._finish(self._extra_delivery(order, code='incoming'))
        self._finish(self._extra_delivery(order, code='internal'))
        self.assertEqual(self._dates(order), before)
        for state in ('6_churn', '5_renewed'):
            order.subscription_state = state
            self._finish(self._extra_delivery(order))
            self.assertEqual(self._dates(order), before)
        # Upsells require a real parent to satisfy the native currency constraint.
        upsell = self._order(confirm=False, state='sale', subscription_state='7_upsell',
                             subscription_id=order.id, pricelist_id=order.pricelist_id.id)
        before_upsell = self._dates(upsell)
        self._finish(self._extra_delivery(upsell))
        self.assertEqual(self._dates(upsell), before_upsell)

    def test_already_posted_invoices_unchanged_and_dates_can_go_back(self):
        order = self._order()
        invoice = order._create_invoices()
        invoice.invoice_date = date(2026, 1, 1)
        invoice.action_post()
        before = invoice.read(['state', 'date', 'amount_total', 'invoice_date'])
        lines = invoice.line_ids.read(['debit', 'credit', 'quantity', 'deferred_start_date', 'deferred_end_date'])
        self._finish(order.picking_ids, datetime(2026, 1, 2, 12))
        self.assertEqual(order.next_invoice_date, date(2026, 1, 5))
        self.assertEqual(invoice.read(['state', 'date', 'amount_total', 'invoice_date']), before)
        self.assertEqual(invoice.line_ids.read(['debit', 'credit', 'quantity', 'deferred_start_date', 'deferred_end_date']), lines)

    def test_native_failure_rolls_back_delivery_and_dates(self):
        order = self._order()
        picking = order.picking_ids
        self._prepare(picking)
        state, dates, messages = picking.state, self._dates(order), order.message_ids.ids
        original = type(order).write
        def reject_activation(records, values):
            if 'start_date' in values and 'end_date' in values:
                raise ValidationError('Native activation rejection')
            return original(records, values)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            with patch.object(type(order), 'write', reject_activation):
                picking.button_validate()
        self.assertEqual((picking.state, self._dates(order), order.message_ids.ids), (state, dates, messages))

    def test_native_quantities_and_multiple_orders(self):
        first, second = self._order(), self._order()
        before = first.order_line.mapped('product_uom_qty')
        self._prepare(first.picking_ids)
        self._prepare(second.picking_ids, datetime(2026, 2, 15, 12))
        (first.picking_ids | second.picking_ids)._action_done()
        self.assertEqual((first.start_date, second.start_date), (date(2026, 2, 2), date(2026, 2, 18)))
        self.assertEqual(first.order_line.mapped('product_uom_qty'), before)
        goods = first.order_line.filtered(lambda line: line.product_id == self.goods)
        self.assertEqual((goods.qty_delivered, goods.qty_to_invoice), (1, 1))

    def test_views_plan_and_permissions(self):
        self.service.subscription_plan_default = self.plan_month
        order = self._order(confirm=False, plan_id=False)
        order.order_line._onchange_date_subs_product_order()
        order._date_subs_apply_default_plan()
        self.assertEqual(order.plan_id, self.plan_month)
        view = self.env['product.template'].get_view(view_id=self.env.ref('product.product_template_only_form_view').id)
        arch = etree.fromstring(view['arch'].encode())
        self.assertEqual(len(arch.xpath("//field[@name='subscription_plan_default']")), 1)
        self.assertEqual(len(arch.xpath("//field[@name='days_to_activate']")), 1)
        readonly_user = new_test_user(self.env, login='activation_readonly', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.goods.product_tmpl_id.with_user(readonly_user).write({'days_to_activate': 8})

    def test_physical_recurring_product_keeps_native_delivery_period_filter(self):
        self.goods.write({'recurring_invoice': True, 'invoice_policy': 'delivery',
            'subscription_rule_ids': [Command.create({'plan_id': self.plan_month.id, 'fixed_price': 10})]})
        order = self._order(order_line=[Command.create({'product_id': self.goods.id, 'product_uom_qty': 1})])
        picking = order.picking_ids
        self._prepare(picking)
        # Delivery before activation is outside the new native billing period.
        with freeze_time('2026-01-30 12:00:00'):
            picking.button_validate()
        self.assertEqual(picking.state, 'done')
        self.assertEqual(order.start_date, date(2026, 2, 2))
        self.assertEqual(picking.move_ids.quantity, 1)
        self.assertEqual(order.order_line.qty_delivered, 0)
        self.assertEqual(order.order_line.qty_to_invoice, 0)
