# Part of Avannubo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, tagged
from odoo.addons.sale_purchase.tests.common import TestCommonSalePurchaseNoChart


@tagged('post_install', '-at_install', 'no_group_purchase19')
class TestPurchaseNoGroupSupplier(TestCommonSalePurchaseNoChart):
    @classmethod
    def get_default_groups(cls):
        return (super().get_default_groups()
            | cls.env.ref('purchase.group_purchase_manager')
            | cls.env.ref('stock.group_stock_manager'))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.partner_vendor_service
        cls.vendor.group_rfq = 'all'
        cls.warehouse = cls.env['stock.warehouse'].search([
            ('company_id', '=', cls.env.company.id)], limit=1)
        cls.rule = cls.warehouse.buy_pull_id
        cls.mto_route = cls.env.ref('stock.route_warehouse0_mto')
        cls.mto_route.active = True
        cls.goods = cls.env['product.product'].create({
            'name': 'Separated purchase goods', 'is_storable': True,
            'list_price': 50, 'taxes_id': False, 'supplier_taxes_id': False,
            'route_ids': [Command.set((cls.mto_route | cls.rule.route_id).ids)],
            'seller_ids': [Command.create({'partner_id': cls.vendor.id, 'price': 23})],
        })

    def _order(self, products=None, company=None):
        products = products or [self.service_purchase_1]
        company = company or self.env.company
        return self.env['sale.order'].with_company(company).create({
            'partner_id': self.partner_a.id, 'company_id': company.id,
            'order_line': [Command.create({
                'product_id': product.id, 'product_uom_qty': 2,
                'price_unit': 50, 'tax_ids': False,
            }) for product in products],
        })

    def _reference(self, order):
        if not order.stock_reference_ids:
            order.stock_reference_ids = self.env['stock.reference'].create({
                'name': order.name, 'sale_ids': [Command.link(order.id)],
            })
        return order.stock_reference_ids

    def _values(self, order=None, line=None):
        values = {
            'date_planned': fields.Datetime.now() + timedelta(days=10),
            'warehouse_id': self.warehouse, 'supplier': self.goods.seller_ids[:1],
        }
        if order:
            values['reference_ids'] = self._reference(order)
        if line:
            values['sale_line_id'] = line.id
        return values

    def _run_buy(self, values_list, rule=None, company=None):
        rule = rule or self.rule
        company = company or self.env.company
        procurements = []
        for values in values_list:
            procurement = self.env['stock.rule'].Procurement(
                self.goods, 2, self.goods.uom_id, rule.location_dest_id,
                self.goods.name, 'Separated procurement', company, values)
            procurements.append((procurement, rule))
        self.env['stock.rule']._run_buy(procurements)

    def _purchases(self):
        return self.env['purchase.order'].search([('partner_id', '=', self.vendor.id)])

    def test_default_and_contact_form(self):
        self.assertTrue(self.vendor.no_group_purchase)
        with Form(self.vendor) as form:
            self.assertFalse(form._get_modifier('no_group_purchase', 'invisible'))
            form.no_group_purchase = False
        self.assertFalse(self.vendor.no_group_purchase)

    def test_services_batch_separates_sales_and_groups_lines(self):
        orders = self._order([self.service_purchase_1, self.service_purchase_2]) | self._order()
        result = orders.order_line._purchase_service_create()
        self.assertEqual(set(result), set(orders.order_line))
        purchases = self._purchases()
        self.assertEqual(len(purchases), 2)
        for purchase in purchases:
            self.assertEqual(len(purchase.order_line.sale_line_id.order_id), 1)
        self.assertEqual(len(purchases.order_line), 3)
        for line, purchase_lines in result.items():
            self.assertEqual(purchase_lines.sale_line_id, line)
            self.assertEqual(purchase_lines.product_qty, 2)
            self.assertEqual(purchase_lines.price_unit, line.product_id.seller_ids.price)

    def test_services_reuse_increase_and_reconfirmation(self):
        order = self._order()
        order.action_confirm()
        purchase = self._purchases()
        order.order_line.product_uom_qty = 5
        self.assertEqual(self._purchases(), purchase)
        self.assertEqual(purchase.order_line.product_qty, 5)
        order._action_cancel()
        order.action_draft()
        order.action_confirm()
        self.assertEqual(self._purchases(), purchase)
        self.assertEqual(len(purchase.order_line), 1)

    def test_services_do_not_reuse_mixed_purchase(self):
        first, second = self._order(), self._order()
        (first | second).order_line._purchase_service_create()
        purchases = self._purchases()
        mixed = purchases[:1]
        (purchases - mixed).order_line.order_id = mixed
        new_line = self.env['sale.order.line'].create({
            'order_id': first.id, 'product_id': self.service_purchase_2.id,
            'product_uom_qty': 2,
        })
        result = new_line._purchase_service_create()
        self.assertNotEqual(result[new_line].order_id, mixed)
        self.assertEqual(result[new_line].order_id.order_line.sale_line_id.order_id, first)

    def test_services_exclude_non_draft_purchases(self):
        for state in ('sent', 'purchase', 'cancel'):
            order = self._order()
            initial = order.order_line._purchase_service_create()[order.order_line].order_id
            initial.write({'state': state})
            created = order.order_line._purchase_service_create()[order.order_line].order_id
            self.assertNotEqual(created, initial)
            self.assertEqual(created.state, 'draft')

    def test_unchecked_services_keep_native_order_separation(self):
        self.vendor.no_group_purchase = False
        orders = self._order() | self._order()
        orders.action_confirm()
        self.assertEqual(len(self._purchases()), 2)

    def test_stock_batch_separation_for_all_native_group_options(self):
        for option in ('default', 'day', 'week', 'all'):
            self.vendor.group_rfq = option
            first, second = self._order([self.goods]), self._order([self.goods])
            first_values, second_values = self._values(first), self._values(second)
            # Both planned dates must be identical for native daily/weekly grouping.
            second_values['date_planned'] = first_values['date_planned']
            first_domain = self.rule._make_po_get_domain(self.env.company, first_values, self.vendor)
            second_domain = self.rule._make_po_get_domain(self.env.company, second_values, self.vendor)
            self.assertNotEqual(first_domain, second_domain)
            hash(first_domain)
            before = self._purchases()
            self._run_buy([first_values, first_values.copy(), second_values])
            created = self._purchases() - before
            self.assertEqual(len(created), 2)
            self.assertEqual(sorted(created.order_line.mapped('product_qty')), [2, 4])
            self.assertEqual(set(created.order_line.mapped('price_unit')), {23})
            self.assertTrue(all(len(po.reference_ids.sale_ids) == 1 for po in created))
            self._run_buy([first_values])
            self.assertEqual(self._purchases() - before, created)

    def test_daily_grouping_keeps_different_planned_dates_separate(self):
        self.vendor.group_rfq = 'day'
        order = self._order([self.goods])
        first_values = self._values(order)
        self._run_buy([first_values])
        initial = self._purchases()
        later_values = dict(first_values, date_planned=first_values['date_planned'] + timedelta(days=1))
        self._run_buy([later_values])
        self.assertEqual(len(self._purchases()), 2)
        self.assertEqual(initial.order_line.product_qty, 2)
        self.assertTrue(all(po.reference_ids.sale_ids == order for po in self._purchases()))

    def test_unchecked_stock_uses_native_grouping(self):
        self.vendor.no_group_purchase = False
        orders = self._order([self.goods]) | self._order([self.goods])
        self._run_buy([self._values(order) for order in orders])
        self.assertEqual(len(self._purchases()), 1)
        self.assertEqual(self._purchases().order_line.product_qty, 4)
        # The native batch initially takes the first procurement's references.
        # Reusing that RFQ in a later run links the remaining native reference.
        self._run_buy([self._values(orders[1])])
        self.assertEqual(self._purchases().reference_ids.sale_ids, orders)

    def test_replenishment_without_sales_uses_native_grouping(self):
        self._run_buy([self._values()])
        initial = self._purchases()
        self._run_buy([self._values()])
        self.assertEqual(self._purchases(), initial)
        self.assertEqual(initial.order_line.product_qty, 4)
        self.assertFalse(initial.reference_ids.sale_ids)

    def test_ambiguous_references_fail_before_creating_batch(self):
        first, second = self._order([self.goods]), self._order([self.goods])
        values = self._values(first)
        values['reference_ids'] |= self._reference(second)
        with self.assertRaises(UserError):
            self._run_buy([self._values(), values])
        self.assertFalse(self._purchases())
        # A sale line has priority over the ambiguous reference set.
        values['sale_line_id'] = first.order_line.id
        domain = self.rule._make_po_get_domain(self.env.company, values, self.vendor)
        self.assertIn(('reference_ids.sale_ids', '=', first.id), domain)

    def test_mto_confirmation_reuses_reference_without_sale_line_on_purchase(self):
        orders = self._order([self.goods, self.goods]) | self._order([self.goods])
        orders.action_confirm()
        purchases = self._purchases()
        self.assertEqual(len(purchases), 2)
        self.assertFalse(purchases.order_line.sale_line_id)
        self.assertTrue(all(len(po.reference_ids.sale_ids) == 1 for po in purchases))
        orders[:1].order_line[:1].product_uom_qty = 3
        self.assertEqual(self._purchases(), purchases)

    def test_stock_does_not_reuse_mixed_reference_purchase(self):
        first, second = self._order([self.goods]), self._order([self.goods])
        self._run_buy([self._values(first)])
        mixed = self._purchases()
        mixed.reference_ids |= self._reference(second)
        self._run_buy([self._values(first)])
        new_purchase = self._purchases() - mixed
        self.assertEqual(len(new_purchase), 1)
        self.assertEqual(new_purchase.reference_ids.sale_ids, first)

    def test_stock_does_not_reuse_non_draft_purchases(self):
        for state in ('sent', 'purchase', 'cancel'):
            order = self._order([self.goods])
            before = self._purchases()
            self._run_buy([self._values(order)])
            initial = self._purchases() - before
            initial.state = state
            self._run_buy([self._values(order)])
            self.assertEqual(len(self._purchases() - before - initial), 1)

    def test_stock_currency_operation_and_company_filters(self):
        order = self._order([self.goods])
        values = self._values(order)
        self._run_buy([values])
        purchase = self._purchases()
        domain = self.rule._make_po_get_domain(self.env.company, values, self.vendor)
        self.assertEqual(self.env['purchase.order'].search(domain), purchase)
        other_currency = self.env['res.currency'].with_context(active_test=False).search([
            ('id', '!=', purchase.currency_id.id)], limit=1)
        other_currency.active = True
        purchase.currency_id = other_currency
        self.assertFalse(self.env['purchase.order'].search(domain))
        purchase.currency_id = self.env.company.currency_id
        original_type = purchase.picking_type_id
        other_type = self.warehouse.out_type_id
        purchase.picking_type_id = other_type
        self.assertFalse(self.env['purchase.order'].search(domain))
        purchase.picking_type_id = original_type
        other_company = self.setup_other_company()['company']
        self.assertFalse(self.env['purchase.order'].search(
            self.rule._make_po_get_domain(other_company, values, self.vendor)))

    def test_services_multiple_companies(self):
        other_company = self.setup_other_company()['company']
        self.service_purchase_1.seller_ids.company_id = False
        orders = self._order() | self._order(company=other_company)
        result = orders.order_line._purchase_service_create()
        self.assertEqual(len(self._purchases()), 2)
        for line, purchases in result.items():
            self.assertEqual(purchases.company_id, line.company_id)

    def test_dropship_separation_and_lot_links(self):
        route = self.env.ref('stock_dropshipping.route_drop_shipping', raise_if_not_found=False)
        if not route:
            self.skipTest('Dropship is tested when its native optional module is installed')
        self.goods.route_ids = route
        orders = self._order([self.goods, self.goods]) | self._order([self.goods])
        if 'lot_id' in self.env['sale.order.line']._fields:
            lots = self.env['stock.lot'].create([
                {'name': 'NO-GROUP-LOT-A', 'product_id': self.goods.id, 'company_id': self.env.company.id},
                {'name': 'NO-GROUP-LOT-B', 'product_id': self.goods.id, 'company_id': self.env.company.id},
            ])
            orders[:1].order_line[0].lot_id = lots[0]
            orders[:1].order_line[1].lot_id = lots[1]
        orders.action_confirm()
        purchases = self._purchases()
        self.assertEqual(len(purchases), 2)
        self.assertEqual(len(purchases.order_line), 3)
        for purchase_line in purchases.order_line:
            self.assertTrue(purchase_line.sale_line_id)
            self.assertEqual(purchase_line.product_qty, 2)
            if 'sale_lot_id' in purchase_line._fields:
                self.assertEqual(purchase_line.sale_lot_id, purchase_line.sale_line_id.lot_id)
