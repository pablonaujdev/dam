# Part of Avannubo. See LICENSE file for full copyright and licensing details.


def sale_purchase_order_domain(sale_order_id):
    """Hashable PO domain for one sale, excluding already mixed purchases.

    MTO uses stock references; service and dropship lines use sale_line_id.
    Tuples are required because _run_buy groups procurements by domain key.
    """
    return (
        '|',
        ('reference_ids.sale_ids', '=', sale_order_id),
        ('order_line.sale_line_id.order_id', '=', sale_order_id),
        ('reference_ids', 'not any', (
            ('sale_ids', 'any', (('id', '!=', sale_order_id),)),
        )),
        ('order_line', 'not any', (
            ('sale_line_id', '!=', False),
            ('sale_line_id.order_id', '!=', sale_order_id),
        )),
    )
