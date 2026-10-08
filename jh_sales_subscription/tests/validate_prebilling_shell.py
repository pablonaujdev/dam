"""Ejecutar solo en la copia MIAC con odoo shell; todas las pruebas hacen rollback."""
from dateutil.relativedelta import relativedelta
from odoo import fields, Command
from odoo.exceptions import UserError, ValidationError


def validate(env):
    env = env(context=dict(env.context, tracking_disable=True, mail_create_nosubscribe=True))
    template = env['sale.order'].browse(7108).exists()
    assert template and template.name == 'S01961', 'Usar la copia de pruebas MIAC.'
    start = fields.Date.today() + relativedelta(days=10)
    end = start + relativedelta(years=1)
    product = env['product.product'].browse(27)

    def create_order(product=product, price=685, start=start, end=end):
        order = env['sale.order'].create({
            'partner_id': template.partner_id.id,
            'pricelist_id': template.pricelist_id.id,
            'plan_id': template.plan_id.id,
            'start_date': start, 'end_date': end,
            'order_line': [Command.create({
                'product_id': product.id, 'product_uom_qty': 1,
                'price_unit': price, 'discount': 0,
            })],
        })
        order.action_confirm()
        assert order.state == 'sale'
        return order

    def invoice(order):
        wizard = env['sale.advance.payment.inv'].create({
            'sale_order_ids': [Command.set(order.ids)],
            'advance_payment_method': 'delivered',
        })
        wizard.create_invoices()
        return order.order_line.invoice_lines.move_id.filtered(lambda m: m.state == 'draft')

    def recompute(order):
        lines = order.order_line
        for name in ('qty_invoiced', 'qty_to_invoice', 'invoice_status'):
            env.add_to_compute(lines._fields[name], lines)
            lines._recompute_recordset([name])
        env.add_to_compute(order._fields['invoice_status'], order)
        order._recompute_recordset(['invoice_status'])

    order = create_order()
    assert order.order_line.qty_delivered == 0
    assert order.invoice_status == order.order_line.invoice_status == 'to invoice'
    assert not order.with_context(recurring_automatic=True)._get_invoiceable_lines()
    print('PASS inicio futuro pendiente y sin factura automatica anticipada')
    move = invoice(order)
    assert len(move) == 1
    assert move.amount_untaxed == 685
    assert order.invoice_status != 'invoiced', 'Un borrador no acredita cobertura contabilizada.'
    try:
        with env.cr.savepoint():
            invoice(order)
        raise AssertionError('Acepto una segunda factura mientras existe un borrador.')
    except ValidationError:
        pass
    print('PASS borrador no marca Facturado ni permite duplicar la factura')
    move.invoice_date = fields.Date.today()
    move.action_post()
    recompute(order)
    assert order.start_date == start and order.end_date == end
    assert order.next_invoice_date == end
    assert order.invoice_status == order.order_line.invoice_status == 'invoiced'
    aml = move.invoice_line_ids.filtered('product_id')
    assert aml.deferred_start_date == start
    assert aml.deferred_end_date == end - relativedelta(days=1)
    print('PASS factura anticipada contabilizada: linea y pedido facturados, fechas intactas')

    before = order.order_line.invoice_lines.move_id.ids
    try:
        with env.cr.savepoint():
            invoice(order)
            assert order.order_line.invoice_lines.move_id.ids == before, 'Factura duplicada fuera del contrato.'
    except UserError:
        pass
    print('PASS no permite una segunda factura fuera del contrato')

    refund = move._reverse_moves(default_values_list=[{'invoice_date': fields.Date.today()}])
    refund.action_post()
    recompute(order)
    assert not order.order_line._jh_has_posted_invoice_coverage(2)
    assert order.invoice_status != 'invoiced'
    assert order.order_line.invoice_status != 'invoiced'
    print('PASS rectificativa completa elimina la cobertura; no se oculta como facturado')

    service = product.copy({'name': 'PRUEBA SERVICIO SOBRE ENTREGADO', 'invoice_policy': 'delivery'})
    service_order = create_order(product=service)
    assert service_order.order_line.qty_delivered == 0
    assert service_order.invoice_status == 'no'
    print('PASS servicio sobre entregado conserva Nada por facturar sin entrega')

    free_order = create_order()
    free_order.order_line.discount = 100
    assert free_order.invoice_status == 'no'
    print('PASS suscripcion gratuita conserva Nada por facturar')

    canceled_order = create_order()
    draft = invoice(canceled_order)
    draft.button_cancel()
    recompute(canceled_order)
    assert canceled_order.invoice_status == canceled_order.order_line.invoice_status == 'to invoice'
    print('PASS factura cancelada antes de contabilizar vuelve a estar pendiente')

    try:
        with env.cr.savepoint():
            create_order(end=start - relativedelta(days=1))
        raise AssertionError('Acepto fin anterior al inicio.')
    except ValidationError:
        pass
    print('PASS rechaza fin anterior al inicio')

    parent = create_order(start=start - relativedelta(years=1), end=end)
    parent.write({'next_invoice_date': start})
    action = parent.prepare_renewal_order()
    renewal = env['sale.order'].browse(action['res_id'])
    renewal.end_date = end
    renewal.action_confirm()
    assert parent.subscription_state == '5_renewed'
    assert renewal.start_date == start
    assert renewal.invoice_status == renewal.order_line.invoice_status == 'to invoice'
    print('PASS renovacion nativa confirmada antes de inicio: A facturar')

    from unittest.mock import patch
    with patch.object(fields.Date, 'today', return_value=start):
        recompute(renewal)
        assert renewal.invoice_status == 'to invoice'
    print('PASS al llegar la fecha de inicio conserva el pendiente')

    current_order = create_order(start=start - relativedelta(years=1))
    old_invoice = env['account.move'].create({
        'move_type': 'out_invoice', 'partner_id': current_order.partner_id.id,
        'invoice_date': fields.Date.today(),
        'invoice_line_ids': [Command.create({
            'product_id': product.id, 'quantity': 1, 'price_unit': 685,
            'sale_line_ids': [Command.set(current_order.order_line.ids)],
            'subscription_id': current_order.id,
            'deferred_start_date': start - relativedelta(years=1),
            'deferred_end_date': start - relativedelta(days=1),
        })],
    })
    old_invoice.action_post()
    current_order.start_date = start
    recompute(current_order)
    assert not current_order.order_line._jh_has_posted_invoice_coverage(2)
    assert current_order.invoice_status != 'invoiced'
    print('PASS una factura de un periodo anterior al inicio no acredita el contrato nuevo')


try:
    validate(env)
finally:
    env.cr.rollback()
    print('ROLLBACK: no se guardan pedidos, facturas ni cambios de prueba')
