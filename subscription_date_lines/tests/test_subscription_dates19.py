from datetime import timedelta

from lxml import etree

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


@tagged('post_install', '-at_install', 'subscription_dates19')
class TestSubscriptionDates19(TestSubscriptionCommon):
    """Rollback-only regressions for the authorized isolated Odoo 19 environment."""

    def _date_order(self, **extra):
        start = fields.Date.today()
        values = {
            'partner_id': self.partner.id,
            'plan_id': self.plan_month.id,
            'start_date': start,
            'next_invoice_date': start,
            'end_date': start + timedelta(days=365),
            'order_line': [Command.create({'product_id': self.product.id, 'product_uom_qty': 1})],
        }
        values.update(extra)
        return self.env['sale.order'].create(values)

    def test_batch_creation_explicit_empty_and_nonrecurring(self):
        order = self._date_order(order_line=[])
        nonrecurring = self.product2.copy({'recurring_invoice': False})
        lines = self.env['sale.order.line'].create([
            {'order_id': order.id, 'product_id': self.product.id},
            {'order_id': order.id, 'product_id': self.product.id,
             'date_subs_start': False, 'date_subs_end': False},
            {'order_id': order.id, 'product_id': nonrecurring.id},
        ])
        self.assertEqual((lines[0].date_subs_start, lines[0].date_subs_end), (order.start_date, order.end_date))
        for line in lines[1:]:
            self.assertFalse(line.date_subs_start)
            self.assertFalse(line.date_subs_end)
        manual_start = order.start_date + timedelta(days=7)
        manual = self.env['sale.order.line'].create({
            'order_id': order.id, 'product_id': self.product.id, 'date_subs_start': manual_start})
        self.assertEqual(manual.date_subs_start, manual_start)

    def test_header_dates_preserve_manual_and_batch_orders(self):
        orders = self._date_order() | self._date_order(start_date=fields.Date.today() + timedelta(days=1),
                                                   next_invoice_date=fields.Date.today() + timedelta(days=1))
        manual = self.env['sale.order.line'].create({
            'order_id': orders[0].id, 'product_id': self.product.id,
            'date_subs_start': fields.Date.today() + timedelta(days=10),
            'date_subs_end': fields.Date.today() + timedelta(days=40)})
        manual_dates = (manual.date_subs_start, manual.date_subs_end)
        automatic = orders.order_line - manual
        new_start = fields.Date.today() + timedelta(days=2)
        new_end = fields.Date.today() + timedelta(days=400)
        orders.write({'start_date': new_start, 'next_invoice_date': new_start, 'end_date': new_end})
        for line in automatic:
            self.assertEqual((line.date_subs_start, line.date_subs_end), (new_start, new_end))
        self.assertEqual((manual.date_subs_start, manual.date_subs_end), manual_dates)

    def test_explicit_line_dates_win_in_same_header_write(self):
        order = self._date_order()
        start = order.start_date + timedelta(days=5)
        end = order.end_date + timedelta(days=5)
        order.write({'start_date': start, 'next_invoice_date': start, 'end_date': end,
                     'order_line': [Command.update(order.order_line.id, {
                         'date_subs_start': False, 'date_subs_end': end + timedelta(days=5)})]})
        self.assertFalse(order.order_line.date_subs_start)
        self.assertEqual(order.order_line.date_subs_end, end + timedelta(days=5))
        order.write({'end_date': False})
        self.assertEqual(order.order_line.date_subs_end, end + timedelta(days=5))

    def test_new_lines_with_simultaneous_header_changes(self):
        order = self._date_order()
        start = order.start_date + timedelta(days=3)
        end = order.end_date + timedelta(days=3)
        order.write({'start_date': start, 'next_invoice_date': start, 'end_date': end,
                     'order_line': [Command.create({'product_id': self.product.id}),
                                    Command.create({'product_id': self.product.id, 'date_subs_start': False})]})
        lines = order.order_line.sorted('id')
        self.assertEqual((lines[1].date_subs_start, lines[1].date_subs_end), (start, end))
        self.assertFalse(lines[2].date_subs_start)
        self.assertEqual(lines[2].date_subs_end, end)

    def test_product_and_order_changes_only_fill_empty_dates(self):
        first = self._date_order(order_line=[])
        second = self._date_order(order_line=[], start_date=first.start_date + timedelta(days=20),
                                  next_invoice_date=first.start_date + timedelta(days=20))
        nonrecurring = self.product2.copy({'recurring_invoice': False})
        line = self.env['sale.order.line'].create({'order_id': first.id, 'product_id': nonrecurring.id})
        line.product_id = self.product
        self.assertEqual(line.date_subs_start, first.start_date)
        line.date_subs_end = False
        line.order_id = second
        self.assertEqual(line.date_subs_start, first.start_date)
        self.assertEqual(line.date_subs_end, second.end_date)

    def test_form_repeated_header_changes_keep_manual_dates(self):
        order = self._date_order()
        manual = self.env['sale.order.line'].create({
            'order_id': order.id, 'product_id': self.product.id,
            'date_subs_start': order.start_date + timedelta(days=10),
            'date_subs_end': order.end_date - timedelta(days=10)})
        manual_dates = (manual.date_subs_start, manual.date_subs_end)
        automatic = order.order_line - manual
        with Form(order, view='sale.view_order_form') as form:
            form.start_date = order.start_date - timedelta(days=1)
            form.start_date = order.start_date - timedelta(days=2)
            form.end_date = order.end_date + timedelta(days=1)
            form.end_date = order.end_date + timedelta(days=2)
        self.assertEqual((automatic.date_subs_start, automatic.date_subs_end), (order.start_date, order.end_date))
        self.assertEqual((manual.date_subs_start, manual.date_subs_end), manual_dates)

    def test_unique_conflicting_and_explicit_plans_orm(self):
        self.product.subscription_plan_default = self.plan_month
        self.product2.subscription_plan_default = self.plan_year
        orders = self.env['sale.order'].create([
            {'partner_id': self.partner.id,
             'order_line': [Command.create({'product_id': self.product.id})]},
            {'partner_id': self.partner.id,
             'order_line': [Command.create({'product_id': self.product.id}),
                            Command.create({'product_id': self.product2.id})]},
            {'partner_id': self.partner.id, 'plan_id': self.plan_week.id,
             'order_line': [Command.create({'product_id': self.product.id})]},
        ])
        self.assertEqual(orders[0].plan_id, self.plan_month)
        self.assertFalse(orders[1].plan_id)
        self.assertEqual(orders[2].plan_id, self.plan_week)
        with self.assertRaises(UserError), self.cr.savepoint():
            orders[1].action_confirm()
        orders[1].plan_id = self.plan_month
        orders[1].action_confirm()
        orders[0].write({'plan_id': False, 'order_line': [Command.update(orders[0].order_line.id, {'product_uom_qty': 2})]})
        self.assertFalse(orders[0].plan_id)

    def test_template_and_one_time_sale(self):
        self.product.subscription_plan_default = self.plan_month
        template = self.env['sale.order.template'].create({'name': 'Dates template', 'plan_id': self.plan_year.id})
        order = self.env['sale.order'].create({'partner_id': self.partner.id,
            'sale_order_template_id': template.id,
            'order_line': [Command.create({'product_id': self.product.id})]})
        self.assertEqual(order.plan_id, self.plan_year)
        self.product.allow_one_time_sale = True
        sale = self.env['sale.order'].create({'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.product.id})]})
        self.assertFalse(sale.plan_id)
        sale.action_confirm()
        self.assertFalse(sale.is_subscription)
        explicit = self.env['sale.order'].create({'partner_id': self.partner.id, 'plan_id': False,
            'order_line': [Command.create({'product_id': self.product.id})]})
        self.assertFalse(explicit.plan_id)

    def test_direct_line_create_and_write_suggest_plan(self):
        self.product.subscription_plan_default = self.plan_month
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.line'].create({'order_id': order.id, 'product_id': self.product.id})
        self.assertEqual(order.plan_id, self.plan_month)
        order.plan_id = False
        line.product_id = self.product
        self.assertEqual(order.plan_id, self.plan_month)

    def test_form_default_plan_conflict_and_manual_choice(self):
        self.product.subscription_plan_default = self.plan_month
        self.product2.subscription_plan_default = self.plan_year
        with Form(self.env['sale.order'], view='sale.view_order_form') as form:
            form.partner_id = self.partner
            with form.order_line.new() as line:
                line.product_id = self.product
            self.assertEqual(form.plan_id, self.plan_month)
            with form.order_line.new() as line:
                line.product_id = self.product2
            self.assertFalse(form.plan_id)
            form.plan_id = self.plan_week
            with form.order_line.edit(0) as line:
                line.product_uom_qty = 2
            self.assertEqual(form.plan_id, self.plan_week)

    def test_renewal_upsell_and_copy_use_new_period(self):
        order = self._date_order(next_invoice_date=fields.Date.today() + timedelta(days=30))
        self.env['sale.order.line'].create({'order_id': order.id, 'product_id': self.product.id})
        order.order_line[0].date_subs_start = order.start_date + timedelta(days=5)
        order.order_line[1].date_subs_end = order.end_date - timedelta(days=5)
        if 'lot_id' in order.order_line._fields:
            lots = self.env['stock.lot'].create([
                {'name': 'DATE-LINE-A', 'product_id': self.product.id},
                {'name': 'DATE-LINE-B', 'product_id': self.product.id}])
            for line, lot in zip(order.order_line, lots):
                line.lot_id = lot
        order.action_confirm()
        for state in ('2_renewal', '7_upsell'):
            values = order.with_context(renewal_pricing_mode='keep_current')._prepare_upsell_renew_order_values(state)
            child = self.env['sale.order'].create(values)
            for line in child.order_line.filtered('recurring_invoice'):
                self.assertEqual((line.date_subs_start, line.date_subs_end), (child.start_date, child.end_date))
                self.assertIn(line.parent_line_id, order.order_line)
                if 'lot_id' in line._fields:
                    self.assertEqual(line.lot_id, line.parent_line_id.lot_id)
        copied = order.copy({'start_date': order.start_date + timedelta(days=40),
                             'next_invoice_date': order.start_date + timedelta(days=40)})
        for line in copied.order_line.filtered('recurring_invoice'):
            self.assertEqual(line.date_subs_start, copied.start_date)

    def test_dates_and_legacy_partial_flag_leave_native_billing(self):
        order = self._date_order()
        order.action_confirm()
        line = order.order_line
        before = (line._get_invoice_line_parameters(), line.qty_to_invoice,
                  line.price_unit, line.discount, order.amount_total)
        line.write({'date_subs_start': order.start_date + timedelta(days=100),
                    'date_subs_end': order.end_date + timedelta(days=100)})
        order.partial_invoice = True
        next_date = order.next_invoice_date + timedelta(days=30)
        order.next_invoice_date = next_date
        self.assertTrue(order.partial_invoice)
        self.assertEqual(order.next_invoice_date, next_date)
        order.next_invoice_date = next_date - timedelta(days=30)
        self.assertEqual((line._get_invoice_line_parameters(), line.qty_to_invoice,
                          line.price_unit, line.discount, order.amount_total), before)

    def test_views_and_read_do_not_rewrite_dates(self):
        order = self._date_order()
        order.order_line.write({'date_subs_start': False, 'date_subs_end': False})
        order.order_line.read(['date_subs_start', 'date_subs_end'])
        self.assertFalse(order.order_line.date_subs_start)
        self.assertFalse(order.order_line.date_subs_end)
        for model, xmlid in (('sale.order', 'sale.view_order_form'),
                             ('product.template', 'product.product_template_only_form_view')):
            arch = self.env[model].get_view(view_id=self.env.ref(xmlid).id, view_type='form')['arch']
            parsed = etree.fromstring(arch.encode())
            expected = 'date_subs_start' if model == 'sale.order' else 'subscription_plan_default'
            self.assertTrue(parsed.xpath("//field[@name='%s']" % expected))
        if self.env['ir.model.data'].search_count([('module', '=', 'miac_line_subscription'),
                                                 ('name', '=', 'view_order_line_subscriptions_tree')]):
            view = self.env.ref('miac_line_subscription.view_order_line_subscriptions_tree')
            arch = etree.fromstring(view.arch_db.encode())
            self.assertTrue(arch.xpath("//field[@name='date_subs_end']"))
            self.assertFalse(arch.xpath("//field[@name='end_date']"))
