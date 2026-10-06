"""Report metadata synchronization. Reads and printing never regenerate data."""
from odoo.tools import is_html_empty


def is_sepa(document):
    codes = {'sepa_direct_debit', 'sdd'}
    method = document.payment_mode_id.payment_method_id
    if hasattr(method, '_get_sdd_payment_method_code'):
        codes.update(method._get_sdd_payment_method_code())
    return method.code in codes


def mandate_bank(document):
    if 'valid_mandate_id' not in document.partner_id._fields:
        return document.env['res.partner.bank']
    mandate = document.partner_id.with_company(document.company_id).valid_mandate_id
    if not mandate or mandate.company_id != document.company_id:
        return document.env['res.partner.bank']
    return mandate.partner_bank_id


def unique(values):
    return list(dict.fromkeys(value for value in values if value))


def source_orders(document):
    if document._name == 'account.move':
        sales = document.invoice_line_ids.sale_line_ids.order_id
        purchases = document.invoice_line_ids.purchase_line_id.order_id
    else:
        sales = document.move_ids.sale_line_id.order_id
        purchases = document.move_ids.purchase_line_id.order_id
        if not sales:
            sales = document.sale_id
        if not purchases:
            purchases = document.purchase_id
    return sales.sorted('id'), purchases.sorted('id')


def source_values(document):
    sales, purchases = source_orders(document)
    orders = sorted(list(sales) + list(purchases), key=lambda order: (order.id, order._name))
    notes = unique(order.note for order in orders if not is_html_empty(order.note))
    return {
        'client_ref': ', '.join(unique(sales.mapped('client_order_ref'))) or False,
        'supplier_ref': ', '.join(unique(purchases.mapped('partner_ref'))) or False,
        'narration' if document._name == 'account.move' else 'notes_print': '\n'.join(notes) or False,
    }


def is_open(document):
    return document.state == 'draft' if document._name == 'account.move' else document.state not in ('done', 'cancel')


def snapshot(documents):
    return {document.id: source_values(document) for document in documents if is_open(document)}


def sync(documents, previous=None, explicit=None, initial=False):
    previous = previous or {}
    explicit = explicit or {}
    for document in documents.exists():
        if not is_open(document):
            continue
        expected = source_values(document)
        old = previous.get(document.id, {})
        protected = explicit.get(document.id, set())
        values = {}
        for field, value in expected.items():
            current = document[field] or False
            if field in protected or current == value:
                continue
            automatic = not current or current == old.get(field, False)
            if initial:
                sales, purchases = source_orders(document)
                first = (sales or purchases)[:1]
                seed = {'client_ref': sales[:1].client_order_ref,
                        'supplier_ref': purchases[:1].partner_ref,
                        'narration': first.note, 'notes_print': first.note}
                automatic = automatic or current == (seed.get(field) or False)
            if automatic:
                values[field] = value
        if values:
            document.with_context(miac_reports_skip_sync=True).write(values)


def related_documents(orders):
    return orders.invoice_ids, orders.picking_ids | orders.order_line.move_ids.picking_id


def line_documents(lines):
    return lines.invoice_lines.move_id, lines.move_ids.picking_id
