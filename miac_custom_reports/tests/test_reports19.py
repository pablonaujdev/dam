"""Run only in the authorized isolated Odoo 19 installation."""
from pathlib import Path

from lxml import html

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tools import config
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged('post_install', '-at_install', 'miac_reports19')
class TestMiacReports19(AccountTestInvoicingCommon):
    @classmethod
    def get_default_groups(cls):
        return (super().get_default_groups() | cls.quick_ref('sales_team.group_sale_manager')
                | cls.quick_ref('purchase.group_purchase_manager') | cls.quick_ref('stock.group_stock_manager')
                | cls.quick_ref('account.group_delivery_invoice_address')
                | cls.quick_ref('stock.group_lot_on_delivery_slip'))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        # wkhtmltopdf runs inside the test container, where 8079 is not its HTTP port.
        cls.env['ir.config_parameter'].sudo().set_param('report.url', 'http://127.0.0.1:%s' % config['http_port'])
        cls.customer = cls.env['res.partner'].create({
            'name': 'MIAC Customer', 'street': 'Fiscal Street 1', 'city': 'Madrid',
            'phone': '+34 910000001', 'lang': 'en_US',
        })
        cls.shipping = cls.env['res.partner'].create({
            'name': 'MIAC Delivery', 'parent_id': cls.customer.id, 'type': 'delivery',
            'street': 'Delivery Street 2', 'phone': '+34 910000002',
        })
        cls.service = cls.env['product.product'].create({
            'name': 'MIAC Service', 'default_code': 'MIAC-SRV', 'type': 'service',
            'invoice_policy': 'order', 'purchase_method': 'purchase',
            'categ_id': cls.product_category.id, 'list_price': 100,
        })
        cls.goods = cls.env['product.product'].create({
            'name': 'MIAC Machine', 'default_code': 'MIAC-MCH', 'type': 'consu',
            'is_storable': True, 'tracking': 'lot', 'invoice_policy': 'order',
            'categ_id': cls.product_category.id,
        })
        cls.lots = cls.env['stock.lot'].create([
            {'name': 'MIAC-LOT-A', 'product_id': cls.goods.id},
            {'name': 'MIAC-LOT-B', 'product_id': cls.goods.id},
        ])
        cls.bank = cls.env['res.partner.bank'].create({
            'partner_id': cls.env.company.partner_id.id,
            'acc_number': 'ES9121000418450200051332', 'company_id': cls.env.company.id,
        })
        cls.journal = cls.company_data['default_journal_bank']
        cls.journal.bank_account_id = cls.bank
        cls.mode = cls.env['account.payment.mode'].create({
            'name': 'MIAC transfer', 'payment_method_id': cls.env.ref('account.account_payment_method_manual_in').id,
            'bank_account_link': 'fixed', 'fixed_journal_id': cls.journal.id,
            'show_bank_account': 'full', 'show_bank_account_from_journal': True,
        })
        tax_group = cls.env['account.tax.group'].create({'name': 'VAT 21%', 'company_id': cls.env.company.id})
        cls.tax = cls.env['account.tax'].create({
            'tax_group_id': tax_group.id, 'name': 'MIAC 21%', 'amount': 21, 'amount_type': 'percent', 'type_tax_use': 'sale',
        })
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)

    def sale(self, reference='REF-A', note='<p>Conditions A</p>', **values):
        return self.env['sale.order'].create({
            'partner_id': self.customer.id, 'partner_shipping_id': self.shipping.id,
            'client_order_ref': reference, 'note': note, 'payment_mode_id': self.mode.id,
            'order_line': [Command.create({'product_id': self.service.id,
                'product_uom_qty': 2, 'price_unit': 100, 'discount': 10,
                'tax_ids': [Command.set(self.tax.ids)]})], **values,
        })

    def purchase(self, reference='SUP-A', note='<p>Supplier conditions</p>'):
        return self.env['purchase.order'].create({
            'partner_id': self.customer.id, 'partner_ref': reference, 'note': note,
            'order_line': [Command.create({'product_id': self.service.id,
                'product_qty': 2, 'price_unit': 80, 'discount': 5,
                'date_planned': fields.Datetime.now()})],
        })

    def invoice(self, orders):
        orders.action_confirm()
        return orders._create_invoices()

    def picking(self, sale_line=None, purchase_line=None):
        picking_type = self.warehouse.out_type_id if sale_line else self.warehouse.in_type_id
        return self.env['stock.picking'].create({
            'partner_id': self.customer.id, 'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'move_ids': [Command.create({
                'product_id': self.goods.id, 'product_uom_qty': 1,
                'product_uom': self.goods.uom_id.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'sale_line_id': sale_line.id if sale_line else False,
                'purchase_line_id': purchase_line.id if purchase_line else False,
            })],
        })

    def render(self, report, document, pdf=False):
        engine = self.env['ir.actions.report'].with_context(discard_logo_check=True, force_report_rendering=True)
        method = engine._render_qweb_pdf if pdf else engine._render_qweb_html
        if pdf:
            with self.allow_pdf_render():
                return method(report, document.ids)[0]
        return method(report, document.ids)[0]

    def test_consolidation_deduplication_and_clearing(self):
        first, second = self.sale(), self.sale('REF-B', '<p>Conditions B</p>')
        invoice = self.invoice(first | second)
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.client_ref, 'REF-A, REF-B')
        self.assertIn('Conditions A', invoice.narration)
        self.assertIn('Conditions B', invoice.narration)
        second.write({'client_order_ref': 'REF-A', 'note': first.note})
        self.assertEqual(invoice.client_ref, 'REF-A')
        self.assertEqual(invoice.narration, first.note)
        (first | second).write({'client_order_ref': False, 'note': False})
        self.assertFalse(invoice.client_ref)
        self.assertFalse(invoice.narration)

    def test_manual_text_and_posted_invoice_preserved(self):
        order = self.sale()
        invoice = self.invoice(order)
        invoice.write({'client_ref': 'MANUAL', 'narration': '<p>Manual text</p>'})
        order.write({'client_order_ref': 'NEW', 'note': '<p>New conditions</p>'})
        self.assertEqual(invoice.client_ref, 'MANUAL')
        self.assertIn('Manual text', invoice.narration)
        invoice.write({'client_ref': order.client_order_ref, 'narration': order.note})
        invoice.action_post()
        order.write({'client_order_ref': False, 'note': False})
        self.assertEqual(invoice.client_ref, 'NEW')
        self.assertIn('New conditions', invoice.narration)

    def test_invoice_links_write_unlink_and_explicit_text(self):
        first, second = self.sale(), self.sale('REF-B', '<p>B</p>')
        invoice = self.invoice(first)
        line = invoice.invoice_line_ids.filtered('product_id')
        line.sale_line_ids = second.order_line
        self.assertEqual(invoice.client_ref, 'REF-B')
        invoice.write({'invoice_line_ids': [Command.update(line.id, {'sale_line_ids': [Command.clear()]})],
                       'client_ref': 'Explicit edit'})
        self.assertEqual(invoice.client_ref, 'Explicit edit')
        self.assertFalse(invoice.narration)
        line.sale_line_ids = first.order_line
        invoice.client_ref = 'REF-A'
        line.unlink()
        self.assertFalse(invoice.client_ref)

    def test_invoice_and_move_batch_creation(self):
        first, second = self.sale(), self.sale('REF-B', '<p>B</p>')
        invoices = self.env['account.move'].create([
            {'move_type': 'out_invoice', 'partner_id': self.customer.id,
             'invoice_line_ids': [Command.create({**order.order_line._prepare_invoice_line(), 'quantity': 1})]}
            for order in (first, second)
        ])
        self.assertEqual(invoices.mapped('client_ref'), ['REF-A', 'REF-B'])
        lines = self.env['account.move.line'].create([
            {'move_id': invoice.id, 'product_id': self.service.id, 'quantity': 1,
             'price_unit': 10, 'sale_line_ids': [Command.set(second.order_line.ids)]}
            for invoice in invoices
        ])
        self.assertEqual(len(lines), 2)
        self.assertEqual(invoices[0].client_ref, 'REF-A, REF-B')

    def test_purchase_notes_and_link_clearing(self):
        order = self.purchase()
        order.button_confirm()
        invoice = self.env['account.move'].create({**order._prepare_invoice(),
            'invoice_line_ids': [Command.create(order.order_line._prepare_account_move_line())]})
        self.assertEqual(invoice.supplier_ref, 'SUP-A')
        picking = self.picking(purchase_line=order.order_line)
        self.assertEqual(picking.supplier_ref, 'SUP-A')
        order.write({'partner_ref': 'SUP-B', 'note': '<p>Changed purchase</p>'})
        self.assertEqual(invoice.supplier_ref, 'SUP-B')
        self.assertEqual(picking.supplier_ref, 'SUP-B')
        self.assertIn('Changed purchase', picking.notes_print)
        picking.move_ids.purchase_line_id = False
        self.assertFalse(picking.supplier_ref)
        invoice.invoice_line_ids.purchase_line_id = False
        self.assertFalse(invoice.supplier_ref)

    def test_picking_manual_closed_and_move_unlink(self):
        order = self.sale()
        picking = self.picking(sale_line=order.order_line)
        self.assertEqual(picking.client_ref, 'REF-A')
        picking.write({'client_ref': 'MANUAL', 'notes_print': '<p>Manual picking</p>'})
        order.client_order_ref = 'REF-B'
        self.assertEqual(picking.client_ref, 'MANUAL')
        picking.client_ref = 'REF-B'
        picking.move_ids.unlink()
        self.assertFalse(picking.client_ref)
        self.assertIn('Manual picking', picking.notes_print)
        # A real completed receipt uses the native validation flow.
        receipt = self.picking(purchase_line=self.purchase().order_line)
        receipt.action_confirm()
        receipt.move_ids.quantity = 1
        receipt.move_line_ids.lot_id = self.lots[0]
        receipt.button_validate()
        self.assertEqual(receipt.state, 'done')
        receipt.move_ids.purchase_line_id.order_id.partner_ref = 'AFTER-DONE'
        self.assertEqual(receipt.supplier_ref, 'SUP-A')

    def test_move_reassignment_and_batch(self):
        first, second = self.sale(), self.sale('REF-B')
        one, two = self.picking(sale_line=first.order_line), self.picking(sale_line=second.order_line)
        move = one.move_ids
        move.sale_line_id = second.order_line
        self.assertEqual(one.client_ref, 'REF-B')
        move.picking_id = two
        self.assertFalse(one.client_ref)
        self.assertEqual(two.client_ref, 'REF-B')
        copies = self.env['stock.move'].create([
            {**move.copy_data()[0], 'picking_id': two.id} for _ in range(2)])
        self.assertEqual(len(copies), 2)

    def test_bank_selection_manual_company_journals_and_sepa(self):
        order = self.sale()
        second_bank = self.bank.copy({'acc_number': 'ES6621000418401234567891'})
        order.partner_bank_id = second_bank
        self.bank.copy({'acc_number': 'ES7921000418451111111111'})
        self.assertEqual(order.partner_bank_id, second_bank)
        self.assertEqual(order.partner_banks_to_show(), self.bank)
        self.mode.show_bank_account_from_journal = False
        self.assertEqual(order.partner_banks_to_show(), second_bank)
        unrelated = self.bank.copy({'partner_id': self.customer.id, 'acc_number': 'ES6621000418400000000011'})
        order.partner_bank_id = unrelated
        self.assertFalse(order.partner_banks_to_show())
        order.partner_bank_id = second_bank
        self.mode.write({'bank_account_link': 'variable', 'variable_journal_ids': [Command.set(self.journal.ids)],
                         'show_bank_account_from_journal': True})
        self.assertEqual(order.partner_banks_to_show(), self.bank)
        sepa = self.env['account.payment.method'].search([('code', '=', 'sepa_direct_debit'), ('payment_type', '=', 'inbound')], limit=1)
        if not sepa:
            sepa = self.env['account.payment.method'].create({'name': 'MIAC SEPA test',
                'code': 'sepa_direct_debit', 'payment_type': 'inbound'})
        self.mode.payment_method_id = sepa
        self.assertFalse(order.partner_banks_to_show())
        invoice = self.invoice(order)
        self.assertFalse(invoice.partner_banks_to_show())
        data = self.setup_other_company()
        other = self.env['sale.order'].with_company(data['company']).create({
            'partner_id': self.customer.id, 'company_id': data['company'].id, 'payment_mode_id': False})
        self.assertEqual(other.bank_partner_id, data['company'].partner_id)
        self.assertFalse(other.partner_bank_id)

    def test_source_line_changes_and_batch_empty_pickings(self):
        first, second = self.sale(), self.sale('REF-B', '<p>B</p>')
        invoice = self.env['account.move'].create({'move_type': 'out_invoice', 'partner_id': self.customer.id,
            'invoice_line_ids': [Command.create({**first.order_line._prepare_invoice_line(), 'quantity': 1})]})
        first.order_line.order_id = second
        self.assertEqual(invoice.client_ref, 'REF-B')
        second.order_line.unlink()
        self.assertFalse(invoice.client_ref)
        self.assertFalse(invoice.narration)
        pickings = self.env['stock.picking'].create([{'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id} for _ in range(2)])
        self.assertEqual(len(pickings), 2)
        self.assertFalse(any(pickings.mapped('client_ref')))
        self.render('stock.action_report_delivery', pickings)

    def test_bank_masking_and_creator_in_sale_html(self):
        order = self.sale()
        order.user_id = False
        for visibility in ('no', 'full', 'first', 'last'):
            self.mode.write({'show_bank_account': visibility, 'show_bank_account_chars': 4})
            page = self.render('sale.action_report_saleorder', order).decode()
            self.assertIn(order.create_uid.name, page)
            expected = {'full': self.bank.acc_number, 'first': self.bank.acc_number[:4] + '*' * 18,
                        'last': '*' * 18 + self.bank.acc_number[-4:]}.get(visibility)
            if expected:
                self.assertIn(expected, page)
            if visibility != 'full':
                self.assertNotIn(self.bank.acc_number, page)
        self.mode.show_bank_account_chars = 0
        self.assertNotIn(self.bank.acc_number, self.render('sale.action_report_saleorder', order).decode())

    def test_invoice_addresses_and_bank_masking(self):
        invoice = self.invoice(self.sale())
        folder = Path('/tmp/miac-report-validation')
        folder.mkdir(exist_ok=True)
        for partner, name in ((self.shipping, 'invoice_shipping'), (self.customer, 'invoice_same_shipping'),
                              (self.env['res.partner'], 'invoice_no_shipping')):
            invoice.partner_shipping_id = partner
            page = self.render('account.account_invoices', invoice).decode()
            self.assertIn('Fiscal Address:', page)
            self.assertIn('Fiscal Street 1', page)
            self.assertIn(self.customer.phone, page)
            if partner == self.shipping:
                self.assertIn('Delivery Street 2', page)
            (folder / (name + '.pdf')).write_bytes(self.render('account.account_invoices', invoice, pdf=True))
        for visibility in ('no', 'full', 'first', 'last'):
            self.mode.write({'show_bank_account': visibility, 'show_bank_account_chars': 4})
            page = self.render('account.account_invoices', invoice).decode()
            if visibility == 'full':
                self.assertIn(self.bank.acc_number, page)
            else:
                self.assertNotIn(self.bank.acc_number, page)
        self.mode.write({'show_bank_account': 'last', 'show_bank_account_chars': 0})
        self.assertNotIn(self.bank.acc_number, self.render('account.account_invoices', invoice).decode())

    def test_html_grouped_sections_lots_and_unchanged_amounts(self):
        order = self.sale(order_line=[
            Command.create({'display_type': 'line_section', 'name': 'MIAC section', 'sequence': 1}),
            Command.create({'display_type': 'line_subsection', 'name': 'MIAC subsection', 'sequence': 2}),
            *[Command.create({'product_id': self.goods.id, 'product_uom_qty': 1, 'price_unit': 100,
                'discount': 10, 'tax_ids': [Command.set(self.tax.ids)], 'lot_id': lot.id, 'sequence': 3 + index})
                for index, lot in enumerate(self.lots)],
        ])
        self.assertAlmostEqual(order.amount_untaxed, 180)
        self.assertAlmostEqual(order.amount_total, 217.8)
        page = html.fromstring(self.render('sale.action_report_saleorder', order))
        self.assertFalse(page.xpath('//th[@name="th_taxes"]'))
        for lot in self.lots:
            self.assertIn(lot.name, page.text_content())
        folder = Path('/tmp/miac-report-validation')
        folder.mkdir(exist_ok=True)
        (folder / 'sale_lots_sections.pdf').write_bytes(self.render('sale.action_report_saleorder', order, pdf=True))
        invoice = self.invoice(order)
        (folder / 'invoice_lots_sections.pdf').write_bytes(self.render('account.account_invoices', invoice, pdf=True))
        self.assertAlmostEqual(invoice.amount_total, order.amount_total)
        page = html.fromstring(self.render('account.account_invoices', invoice))
        self.assertFalse(page.xpath('//th[@name="th_taxes"]'))
        for lot in self.lots:
            self.assertIn(lot.name, page.text_content())
        order.order_line.filtered(lambda line: line.display_type == 'line_section').collapse_composition = True
        page = html.fromstring(self.render('sale.action_report_saleorder', order))
        self.assertTrue(page.xpath('//td[@name="td_lot_grouped"]'))
        self.assertFalse(page.xpath('//td[@name="td_lot_grouped"]//span'))
        invoice.invoice_line_ids.filtered(lambda line: line.display_type in ('line_section', 'line_subsection')).collapse_composition = True
        page = html.fromstring(self.render('account.account_invoices', invoice))
        self.assertTrue(page.xpath('//td[@name="td_lot_grouped"]'))
        self.assertFalse(page.xpath('//td[@name="td_lot_grouped"]//span'))
        (folder / 'sale_grouped.pdf').write_bytes(self.render('sale.action_report_saleorder', order, pdf=True))
        (folder / 'invoice_grouped.pdf').write_bytes(self.render('account.account_invoices', invoice, pdf=True))

    def test_html_pdf_all_document_flows(self):
        order = self.sale()
        purchase = self.purchase()
        incoming = self.picking(purchase_line=purchase.order_line)
        outgoing = self.picking(sale_line=order.order_line)
        cases = [('quotation', 'sale.action_report_saleorder', order),
                 ('proforma', 'sale.action_report_pro_forma_invoice', order),
                 ('purchase_rfq', 'purchase.action_report_purchase_order', purchase),
                 ('receipt', 'stock.action_report_delivery', incoming),
                 ('delivery', 'stock.action_report_delivery', outgoing)]
        # Render drafts before confirmation, then native confirmed documents.
        folder = Path('/tmp/miac-report-validation')
        folder.mkdir(exist_ok=True)
        def export(name, report, document):
            amounts = (document.amount_untaxed, document.amount_total) if 'amount_total' in document._fields else None
            content = self.render(report, document)
            self.assertIn(b'MIAC', content)
            if name in ('receipt_done', 'delivery_done'):
                self.assertIn(b'MIAC-LOT-A', content)
            (folder / (name + '.html')).write_bytes(content)
            pdf = self.render(report, document, pdf=True)
            self.assertTrue(pdf.startswith(b'%PDF'))
            (folder / (name + '.pdf')).write_bytes(pdf)
            if amounts:
                self.assertEqual(amounts, (document.amount_untaxed, document.amount_total))
        for case in cases:
            export(*case)
        incoming.action_confirm()
        incoming.move_ids.quantity = 1
        incoming.move_line_ids.lot_id = self.lots[0]
        incoming.button_validate()
        self.assertEqual(incoming.state, 'done')
        export('receipt_done', 'stock.action_report_delivery', incoming)
        outgoing.action_confirm()
        outgoing.action_assign()
        outgoing.move_ids.quantity = 1
        outgoing.move_line_ids.lot_id = self.lots[0]
        outgoing.button_validate()
        self.assertEqual(outgoing.state, 'done')
        export('delivery_done', 'stock.action_report_delivery', outgoing)
        invoice = self.invoice(order)
        invoice.action_post()
        purchase.button_confirm()
        refund = invoice._reverse_moves(default_values_list=[{'ref': 'MIAC credit note'}])
        for case in [('sale_order', 'sale.action_report_saleorder', order),
                     ('purchase_order', 'purchase.action_report_purchase_order', purchase),
                     ('invoice', 'account.account_invoices', invoice),
                     ('refund', 'account.account_invoices', refund)]:
            export(*case)
        long_order = self.sale(order_line=[Command.create({'product_id': self.service.id,
            'name': 'MIAC long line %02d - Installation and maintenance of equipment' % index,
            'product_uom_qty': 1, 'price_unit': 100, 'discount': 10,
            'tax_ids': [Command.set(self.tax.ids)]}) for index in range(75)])
        export('multipage_sale', 'sale.action_report_saleorder', long_order)
        advance_order = self.sale()
        advance_order.action_confirm()
        self.env['sale.advance.payment.inv'].create({'advance_payment_method': 'fixed',
            'fixed_amount': 5, 'sale_order_ids': [Command.set(advance_order.ids)]}).create_invoices()
        self.assertTrue(advance_order.order_line.filtered('is_downpayment'))
        export('sale_downpayment', 'sale.action_report_saleorder', advance_order)
