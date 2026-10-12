# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class CommissionSettlementLine(models.Model):

    _inherit = 'commission.settlement.line'

    invoiced_quantity = fields.Float(string='Quantity Invoiced', related='invoice_line_id.quantity', store=True, readonly=True, help='Shows the quantity of the source invoice line in the commission settlement.\nUses the original quantity, including refunds; without an invoice line it is zero.')



