# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    subscription_state = fields.Selection(
        related='order_id.subscription_state', store=True
    )

