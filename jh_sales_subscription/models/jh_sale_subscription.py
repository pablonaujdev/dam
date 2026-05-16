# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrderInheritSubscriptionProducts(models.Model):
    _inherit = 'sale.order'

    # Productos asociados a la orden/suscripción (desde order_line).
    jh_subscription_product_ids = fields.Many2many(
        'product.product',
        string='Productos asociados',
        compute='_compute_jh_subscription_products',
        help='Productos de las líneas de esta orden/suscripción. Solo visualización.',
    )
    jh_subscription_products_display = fields.Char(
        string='Productos',
        compute='_compute_jh_subscription_products',
        help='Productos concatenados para la lista. Para ver el detalle, abra la orden.',
    )

    jh_serial_number = fields.Char(string='Lote Num Serie', compute='_compute_jh_serial_number')

    @api.depends('order_line', 'order_line.product_id')
    def _compute_jh_subscription_products(self):
        for order in self:
            products = order.order_line.mapped('product_id') if order.order_line else self.env['product.product']
            order.jh_subscription_product_ids = products
            order.jh_subscription_products_display = ', '.join(products.mapped('display_name')) if products else ''

    @api.depends('order_line', 'order_line.product_id')
    def _compute_jh_serial_number(self):
        for order in self:
            serial_numbers = []
            if order.order_line:
                serial_numbers = order.order_line.mapped('lot_id.name')

            order.jh_serial_number = ', '.join(serial_numbers)
