"""Navigation only: supplier selection, prices and ACLs remain native."""
import ast
from datetime import timedelta

from lxml import etree

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged('post_install', '-at_install', 'miac_pricelist_menu19')
class TestMiacPricelistMenu19(AccountTestInvoicingCommon):
    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.quick_ref('purchase.group_purchase_manager')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.action = cls.env.ref('miac_purchase_pricelist_menu.product_supplierinfo_action')
        cls.view = cls.env.ref('miac_purchase_pricelist_menu.miac_view_product_supplierinfo_view_tree')
        cls.context = ast.literal_eval(cls.action.context)
        cls.vendor = cls.env['res.partner'].create({'name': 'PRICELIST19 Vendor'})
        attribute = cls.env['product.attribute'].create({'name': 'PRICELIST19 Finish',
            'value_ids': [Command.create({'name': name}) for name in ('A', 'B')]})
        cls.template = cls.env['product.template'].create({'name': 'PRICELIST19 Product',
            'type': 'consu', 'attribute_line_ids': [Command.create({'attribute_id': attribute.id,
                'value_ids': [Command.set(attribute.value_ids.ids)]})]})
        cls.variant = cls.template.product_variant_ids[0]

    def tariff(self, **values):
        return self.env['product.supplierinfo'].create({'partner_id': self.vendor.id,
            'product_tmpl_id': self.template.id, 'price': 100,
            'currency_id': self.env.company.currency_id.id, **values})

    def make_user(self, name, group):
        return self.env['res.users'].create({'name': name, 'login': name,
            'company_id': self.env.company.id, 'company_ids': [Command.set(self.env.company.ids)],
            'group_ids': [Command.set(self.env.ref(group).ids)]})

    def test_exact_columns_action_and_translation(self):
        columns = self.view._get_combined_arch().xpath('/list/field')
        self.assertEqual([field.get('name') for field in columns], [
            'partner_id', 'product_tmpl_id', 'product_id', 'price', 'currency_id', 'delay',
            'product_name', 'product_code', 'date_start', 'date_end', 'min_qty', 'discount'])
        self.assertEqual([field.get('optional') for field in columns],
            [None, None, 'show', None, None, 'show', 'hide', 'hide', 'hide', 'hide', 'hide', 'hide'])
        self.assertFalse(self.view._get_combined_arch().get('editable'))
        self.assertFalse(self.view._get_combined_arch().get('multi_edit'))
        self.assertEqual(self.action.view_mode, 'list,form')
        self.assertEqual(self.action.views, [(self.view.id, 'list'),
            (self.env.ref('product.product_supplierinfo_form_view').id, 'form')])
        self.assertEqual(self.context, {'visible_product_tmpl_id': False})
        self.assertFalse(self.action.domain)
        menu = self.env.ref('miac_purchase_pricelist_menu.menu_product_supplierinfo_s')
        self.assertEqual(menu.parent_id, self.env.ref('purchase.menu_purchase_products'))
        self.assertEqual(menu.sequence, 40)
        self.assertEqual(menu.action, self.action)
        self.assertEqual(menu.with_context(lang='es_ES').name, 'Tarifas de Proveedor')
        self.assertEqual(self.action.with_context(lang='es_ES').name, 'Tarifas de Proveedor')
        self.assertTrue(self.env.ref('purchase.menu_product_pricelist_action2_purchase').action)

    def test_native_form_creation_and_edit_permissions(self):
        manager = self.make_user('pricelist19-manager', 'purchase.group_purchase_manager')
        model = self.env['product.supplierinfo'].with_user(manager).with_context(**self.context)
        record = model.create({'partner_id': self.vendor.id, 'product_tmpl_id': self.template.id,
            'product_id': self.variant.id, 'price': 40, 'discount': 5})
        record.write({'price': 50, 'discount': 10, 'product_name': 'Vendor name', 'product_code': 'V-19'})
        self.assertEqual(record.product_tmpl_id, self.template)
        self.assertEqual(record.price, 50)
        self.assertEqual(record.discount, 10)
        arch = etree.fromstring(model.get_view(view_id=self.env.ref('product.product_supplierinfo_form_view').id,
            view_type='form')['arch'].encode())
        self.assertTrue(arch.xpath('//field[@name="product_tmpl_id"]'))
        self.assertFalse(self.context['visible_product_tmpl_id'])
        self.assertTrue(arch.xpath('//field[@name="company_id"]'))

    def test_variants_quantity_discount_and_purchase_price(self):
        general = self.tariff(price=100)
        specific = self.tariff(product_id=self.variant.id, min_qty=5, price=80, discount=10)
        self.assertEqual(self.variant._select_seller(partner_id=self.vendor, quantity=1), general)
        self.assertEqual(self.variant._select_seller(partner_id=self.vendor, quantity=5), specific)
        sibling = self.template.product_variant_ids - self.variant
        self.assertEqual(sibling._select_seller(partner_id=self.vendor, quantity=5), general)
        with Form(self.env['purchase.order']) as form:
            form.partner_id = self.vendor
            with form.order_line.new() as line:
                line.product_id = self.variant
                line.product_qty = 5
        order = form.record
        self.assertEqual(order.order_line.price_unit, 80)
        self.assertEqual(order.order_line.discount, 10)
        self.assertEqual(order.order_line.price_unit_discounted, 72)
        before = order.order_line.price_unit, order.order_line.discount, order.amount_total
        self.env['product.supplierinfo'].with_context(**self.context).get_view(view_id=self.view.id, view_type='list')
        self.env['product.supplierinfo'].with_context(**self.context).search([])
        self.assertEqual(self.variant._select_seller(partner_id=self.vendor, quantity=5), specific)
        self.assertEqual(before, (order.order_line.price_unit, order.order_line.discount, order.amount_total))

    def test_dates_and_no_default_filter(self):
        today = fields.Date.today()
        expired = self.tariff(price=10, date_end=today - timedelta(days=1))
        future = self.tariff(price=20, date_start=today + timedelta(days=1))
        current = self.tariff(price=30, date_start=today, date_end=today)
        all_records = self.env['product.supplierinfo'].with_context(**self.context).search([
            ('product_tmpl_id', '=', self.template.id)])
        self.assertEqual(set(all_records.ids), set((expired | future | current).ids))
        self.assertEqual(self.variant._select_seller(partner_id=self.vendor, quantity=1, date=today), current)
        self.template.active = False
        self.assertEqual(set(self.env['product.supplierinfo'].with_context(**self.context).search([
            ('id', 'in', all_records.ids)]).ids), set(all_records.ids))

    def test_native_units_and_currencies(self):
        dozen = self.env.ref('uom.product_uom_dozen')
        tariff = self.tariff(price=120, discount=10, product_uom_id=dozen.id)
        self.assertAlmostEqual(tariff.price_discounted, 9)
        self.assertEqual(tariff.product_uom_id, dozen)
        other_currency = self.env['res.currency'].create({'name': 'P19', 'symbol': 'P19', 'rounding': 0.01})
        self.env['res.currency.rate'].create({'currency_id': other_currency.id,
            'company_id': self.env.company.id, 'name': fields.Date.today(), 'rate': 2})
        alternate = self.tariff(price=150, currency_id=other_currency.id)
        self.assertEqual(alternate.currency_id, other_currency)
        selected_before = self.variant._select_seller(partner_id=self.vendor, quantity=12)
        self.env['product.supplierinfo'].with_context(**self.context).search([('partner_id', '=', self.vendor.id)])
        self.assertEqual(self.variant._select_seller(partner_id=self.vendor, quantity=12), selected_before)

    def test_readonly_users_and_company_rules(self):
        record = self.tariff()
        buyer = self.make_user('pricelist19-reader', 'purchase.group_purchase_user')
        self.assertEqual(record.with_user(buyer).read(['price'])[0]['price'], 100)
        with self.assertRaises(AccessError):
            record.with_user(buyer).write({'price': 101})
        with self.assertRaises(AccessError):
            self.env['product.supplierinfo'].with_user(buyer).create({'partner_id': self.vendor.id,
                'product_tmpl_id': self.template.id, 'price': 101})
        with self.assertRaises(AccessError):
            record.with_user(buyer).unlink()
        shared = self.tariff(company_id=False)
        other = self.setup_other_company()['company']
        foreign = self.env['product.supplierinfo'].with_company(other).create({'partner_id': self.vendor.id,
            'product_tmpl_id': self.template.id, 'company_id': other.id, 'price': 200})
        records = self.env['product.supplierinfo'].with_user(buyer).search([
            ('id', 'in', (record | shared | foreign).ids)])
        self.assertEqual(set(records.ids), set((record | shared).ids))
