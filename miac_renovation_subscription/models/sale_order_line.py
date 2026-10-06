# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from datetime import datetime
from dateutil.relativedelta import relativedelta

class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    categ_id = fields.Many2one(related='product_id.categ_id', readonly=True)
    order_renove = fields.Many2one(related='order_id.order_renove', string='Order Renove', readonly=True)
    subscription_id = fields.Many2one(related='order_id.subscription_id', string='Subscription Renove', readonly=True)
    start_date = fields.Date(related='order_id.start_date', store=True)
    end_date = fields.Date(related='order_id.end_date', store=True)
    subscription_state = fields.Selection(related='order_id.subscription_state')

    @api.depends('lot_id', 'order_id.subscription_id.order_line.lot_id')
    def _compute_parent_line_id(self):
        super()._compute_parent_line_id()
        for line in self:
            parent = line.parent_line_id
            if not parent or not line.lot_id or parent.lot_id == line.lot_id:
                continue
            # Native matching cannot distinguish equal products/prices by lot.
            # Restrict the correction to candidates with the same native keys.
            candidates = line.order_id.subscription_id.order_line.filtered(
                lambda source: source.lot_id == line.lot_id
                and source.product_id == line.product_id
                and source.product_uom_id == line.product_uom_id
                and source.order_id.currency_id == line.order_id.currency_id
                and source.order_id.plan_id == line.order_id.plan_id
                and line.currency_id.compare_amounts(source.price_unit, line.price_unit) == 0
            )
            # Never select an arbitrary source if a lot is reused on several lines.
            line.parent_line_id = candidates if len(candidates) == 1 else False








