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








