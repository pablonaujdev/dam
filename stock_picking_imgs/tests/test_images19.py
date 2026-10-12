"""Image rendering regressions for the isolated Odoo 19 installation."""
from base64 import b64decode, b64encode
from io import BytesIO
from pathlib import Path

from PIL import Image
from lxml import html

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import config
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.addons.sale.tests.common import TestSaleCommon


@tagged('post_install', '-at_install', 'picking_images19')
class TestPickingImages19(TestSaleCommon):
    @classmethod
    def get_default_groups(cls):
        return (super().get_default_groups()
                | cls.quick_ref('sales_team.group_sale_manager')
                | cls.quick_ref('stock.group_stock_manager'))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.env['ir.config_parameter'].sudo().set_param(
            'report.url', 'http://127.0.0.1:%s' % config['http_port'])
        cls.landscape = cls.png((128, 64), '#2563eb')
        cls.portrait = cls.png((64, 128), '#d97706')
        cls.customer = cls.env['res.partner'].create({'name': 'IMAGE19 Customer', 'lang': 'en_US'})
        cls.goods, cls.empty = cls.env['product.product'].create([
            {'name': 'IMAGE19 Landscape', 'type': 'consu', 'image_1920': cls.landscape,
             'invoice_policy': 'order', 'list_price': 100},
            {'name': 'IMAGE19 No image', 'type': 'consu', 'invoice_policy': 'order', 'list_price': 100},
        ])
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.artifacts = Path('/var/lib/odoo/picking-images19-validation')
        cls.artifacts.mkdir(exist_ok=True)

    @staticmethod
    def png(size, color):
        stream = BytesIO()
        Image.new('RGB', size, color).save(stream, format='PNG')
        return b64encode(stream.getvalue())

    def line_values(self, product=None, **values):
        return {'product_id': (product or self.goods).id, 'product_uom_qty': 2,
                'price_unit': 100, 'discount': 10, **values}

    def sale(self, lines=None):
        return self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create(values) for values in (lines or [self.line_values()])],
        })

    def picking(self, quantity=2, picking_type=None):
        operation = picking_type or self.warehouse.in_type_id
        return self.env['stock.picking'].create({
            'partner_id': self.customer.id, 'picking_type_id': operation.id,
            'location_id': operation.default_location_src_id.id,
            'location_dest_id': operation.default_location_dest_id.id,
            'move_ids': [Command.create({
                'product_id': self.goods.id, 'product_uom_qty': quantity,
                'product_uom': self.goods.uom_id.id,
                'location_id': operation.default_location_src_id.id,
                'location_dest_id': operation.default_location_dest_id.id,
            })],
        })

    def render(self, report, document, name=None):
        engine = self.env['ir.actions.report'].with_context(
            discard_logo_check=True, force_report_rendering=True)
        content = engine._render_qweb_html(report, document.ids)[0]
        if name:
            (self.artifacts / (name + '.html')).write_bytes(content)
            with self.allow_pdf_render():
                pdf = engine._render_qweb_pdf(report, document.ids)[0]
            self.assertTrue(pdf.startswith(b'%PDF'))
            (self.artifacts / (name + '.pdf')).write_bytes(pdf)
        return html.fromstring(content)

    def assert_sale_alignment(self, page):
        columns = len(page.xpath('//table[contains(concat(" ", normalize-space(@class), " "), " o_main_table ")]/thead/tr/th'))
        for row in page.xpath('//tr[@name="tr_product" or @name="tr_combo" or @name="tr_section" or @name="tr_section_group"]'):
            cells = row.xpath('./td')
            if any(cell.get('colspan') == '99' for cell in cells):
                continue
            self.assertEqual(sum(int(cell.get('colspan', '1')) for cell in cells), columns)

    def test_related_fields_and_current_product_image(self):
        order, picking = self.sale(), self.picking()
        picking.action_confirm()
        picking.move_ids.quantity = 1
        records = [order.order_line, picking.move_ids, picking.move_line_ids]
        for record in records:
            field = record._fields['image']
            self.assertFalse(field.store)
            self.assertTrue(field.readonly)
            self.assertFalse(field.compute_sudo)
            self.assertEqual(record.image, self.goods.image_128)
        self.goods.image_1920 = self.portrait
        for record in records:
            self.assertEqual(record.image, self.goods.image_128)
        self.assertNotEqual(order.order_line.image, self.landscape)
        order.order_line.product_id = self.empty
        self.assertFalse(order.order_line.image)

    def test_variant_image_and_no_image(self):
        attribute = self.env['product.attribute'].create({'name': 'IMAGE19 Finish',
            'value_ids': [Command.create({'name': name}) for name in ('Blue', 'Orange')]})
        template = self.env['product.template'].create({'name': 'IMAGE19 Variant',
            'type': 'consu', 'image_1920': self.landscape,
            'attribute_line_ids': [Command.create({'attribute_id': attribute.id,
                'value_ids': [Command.set(attribute.value_ids.ids)]})]})
        self.assertEqual(len(template.product_variant_ids), 2)
        variant = template.product_variant_ids[0]
        variant.image_variant_1920 = self.portrait
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(Image.open(BytesIO(b64decode(variant.image_128))).size, (64, 128))
        order = self.sale([self.line_values(variant), self.line_values(self.empty)])
        self.assertEqual(order.order_line[0].image, variant.image_128)
        self.assertFalse(order.order_line[1].image)
        page = self.render('sale.action_report_saleorder', order)
        self.assertEqual(len(page.xpath('//td[@name="td_image"]//img')), 1)
        self.assertEqual(len(page.xpath('//td[@name="td_image"]')), 2)

    def test_form_thumbnails_and_original_xml_ids(self):
        for view, field in [('sale.view_order_form', 'order_line'), ('stock.view_picking_form', 'move_ids')]:
            arch = self.env.ref(view)._get_combined_arch()
            image = arch.xpath('//field[@name="%s"]/list/field[@name="image"]' % field)
            self.assertEqual(len(image), 1)
            self.assertIn('48', image[0].get('options'))
            self.assertEqual(image[0].getnext().get('name'), 'product_id')
        for xml_id in ('sale_order_image_form_view', 'stock_picking_image_form_view',
                       'image_sale_order_report', 'report_delivery_image_document'):
            self.assertTrue(self.env.ref('stock_picking_imgs.' + xml_id))

    def test_sales_images_sections_notes_and_totals(self):
        order = self.sale([
            {'display_type': 'line_section', 'name': 'IMAGE19 Section', 'sequence': 1},
            {'display_type': 'line_subsection', 'name': 'IMAGE19 Subsection', 'sequence': 2},
            self.line_values(sequence=3), self.line_values(self.empty, sequence=4),
            {'display_type': 'line_note', 'name': 'IMAGE19 Note', 'sequence': 5},
        ])
        amounts = order.amount_untaxed, order.amount_tax, order.amount_total
        page = self.render('sale.action_report_saleorder', order, 'quotation')
        self.assertEqual(len(page.xpath('//td[@name="td_image"]//img')), 1)
        self.assert_sale_alignment(page)
        self.assertIn('IMAGE19 Note', page.text_content())
        self.assertEqual(amounts, (order.amount_untaxed, order.amount_tax, order.amount_total))
        self.assertEqual(order.amount_untaxed, 360)
        self.render('sale.action_report_pro_forma_invoice', order, 'proforma')
        order.action_confirm()
        self.render('sale.action_report_saleorder', order, 'sale_order')

    def test_grouped_summary_has_no_arbitrary_image(self):
        order = self.sale([
            {'display_type': 'line_section', 'name': 'IMAGE19 Group', 'sequence': 1},
            self.line_values(sequence=2), self.line_values(self.empty, sequence=3),
        ])
        order.order_line[0].collapse_composition = True
        page = self.render('sale.action_report_saleorder', order, 'grouped_summary')
        cells = page.xpath('//td[@name="td_grouped_image"]')
        self.assertTrue(cells)
        self.assertFalse(page.xpath('//td[@name="td_grouped_image"]//img'))
        self.assert_sale_alignment(page)

    def test_combo_images_and_alignment(self):
        combo = self.env['product.combo'].create({'name': 'IMAGE19 Choice',
            'combo_item_ids': [Command.create({'product_id': self.goods.id})]})
        product = self.env['product.product'].create({'name': 'IMAGE19 Combo', 'type': 'combo',
            'combo_ids': [Command.link(combo.id)], 'image_1920': self.portrait})
        order = self.sale([self.line_values(product, price_unit=0)])
        order.write({'order_line': [Command.create(self.line_values(
            combo_item_id=combo.combo_item_ids.id, linked_line_id=order.order_line.id))]})
        page = self.render('sale.action_report_saleorder', order, 'combo')
        self.assertTrue(page.xpath('//td[@name="td_combo_image"]//img'))
        self.assert_sale_alignment(page)

    def test_pending_main_table_and_done_report(self):
        picking = self.picking()
        picking.action_confirm()
        page = self.render('stock.action_report_delivery', picking, 'pending_receipt')
        self.assertEqual(len(page.xpath('//table[@name="stock_move_table"]//td[@name="td_image"]//img')), 1)
        picking.move_ids.quantity = 2
        picking.button_validate()
        self.assertEqual(picking.state, 'done')
        page = self.render('stock.action_report_delivery', picking, 'done_receipt')
        self.assertFalse(page.xpath('//table//td[@name="td_image"]'))
        self.assertFalse(page.xpath('//table//th[@name="th_sm_image"]'))
        delivery = self.picking(picking_type=self.warehouse.out_type_id)
        delivery.action_confirm()
        self.render('stock.action_report_delivery', delivery, 'pending_delivery')

    def test_partial_backorder_has_images_only_in_own_main_table(self):
        picking = self.picking(quantity=3)
        picking.action_confirm()
        picking.move_ids.quantity = 1
        action = picking.button_validate()
        self.assertEqual(action['res_model'], 'stock.backorder.confirmation')
        wizard = self.env[action['res_model']].with_context(action['context']).create({})
        wizard.process()
        self.assertEqual(picking.state, 'done')
        backorder = picking.backorder_ids
        self.assertEqual(len(backorder), 1)
        page = self.render('stock.action_report_delivery', picking, 'partial_done')
        self.assertTrue(page.xpath('//table[@name="stock_backorder_table"]'))
        self.assertFalse(page.xpath('//table//td[@name="td_image"]'))
        page = self.render('stock.action_report_delivery', backorder, 'pending_backorder')
        self.assertTrue(page.xpath('//table[@name="stock_move_table"]//td[@name="td_image"]//img'))

    def test_multipage_portrait_landscape_and_lots(self):
        portrait = self.env['product.product'].create({'name': 'IMAGE19 Portrait',
            'type': 'consu', 'invoice_policy': 'order', 'image_1920': self.portrait})
        order = self.sale([self.line_values(portrait if index % 2 else self.goods,
            name='IMAGE19 Item %02d - Equipment with product illustration' % index,
            sequence=index) for index in range(18)])
        page = self.render('sale.action_report_saleorder', order, 'multipage_sale')
        self.assertEqual(len(page.xpath('//td[@name="td_image"]//img')), 18)
        dimensions = set()
        for image in page.xpath('//td[@name="td_image"]//img'):
            self.assertIn('max-height:80pt', image.get('style'))
            self.assertIn('max-width:80pt', image.get('style'))
            dimensions.add(Image.open(BytesIO(b64decode(image.get('src').split(',')[1]))).size)
        self.assertEqual(dimensions, {(128, 64), (64, 128)})
        self.assert_sale_alignment(page)
        if 'lot_id' in order.order_line._fields:
            self.goods.tracking = 'lot'
            lots = self.env['stock.lot'].create([
                {'name': name, 'product_id': self.goods.id} for name in ('IMAGE19-LOT-A', 'IMAGE19-LOT-B')])
            order = self.sale([self.line_values(lot_id=lot.id) for lot in lots])
            page = self.render('sale.action_report_saleorder', order, 'repeated_product_lots')
            for lot in lots:
                self.assertIn(lot.name, page.text_content())
            self.assert_sale_alignment(page)

    def test_downpayment_retains_native_amounts(self):
        order = self.sale()
        order.action_confirm()
        amounts = order.amount_untaxed, order.amount_tax, order.amount_total
        self.env['sale.advance.payment.inv'].create({'advance_payment_method': 'fixed',
            'fixed_amount': 5, 'sale_order_ids': [Command.set(order.ids)]}).create_invoices()
        self.assertTrue(order.order_line.filtered('is_downpayment'))
        self.render('sale.action_report_saleorder', order, 'downpayment')
        self.assertEqual(amounts, (order.amount_untaxed, order.amount_tax, order.amount_total))

    def test_sales_user_and_company_access(self):
        user = self.company_data['default_user_salesman']
        order = self.sale()
        order.user_id = user
        self.assertEqual(order.order_line.with_user(user).image, self.goods.image_128)
        other = self.setup_other_company()['company']
        product = self.goods.copy({'company_id': other.id})
        foreign_order = self.env['sale.order'].with_company(other).create({
            'company_id': other.id, 'partner_id': self.customer.id,
            'order_line': [Command.create(self.line_values(product))],
        })
        with self.assertRaises(AccessError):
            foreign_order.order_line.with_user(user).read(['image'])

    def test_completed_lot_and_package_tables_have_no_images(self):
        self.goods.write({'is_storable': True, 'tracking': 'lot'})
        lot = self.env['stock.lot'].create({'name': 'IMAGE19-DONE-LOT', 'product_id': self.goods.id})
        package = self.env['stock.package'].create({'name': 'IMAGE19-PACKAGE'})
        picking = self.picking()
        picking.action_confirm()
        picking.move_ids.quantity = 2
        picking.move_line_ids.write({'lot_id': lot.id, 'result_package_id': package.id})
        picking.button_validate()
        self.assertEqual(picking.state, 'done')
        page = self.render('stock.action_report_delivery', picking, 'done_lot_package')
        self.assertIn(package.name, page.text_content())
        self.assertFalse(page.xpath('//table//td[@name="td_image"]'))
        self.assertFalse(page.xpath('//table//th[@name="th_sm_image"]'))
