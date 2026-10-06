# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class PurchaseOrderLine(models.Model):

    _inherit = 'purchase.order.line'

    sale_lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial Number', readonly=True, copy=False,
        help="Lot/Serial Number of the product to unbuild.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for line in records:
            if line.sale_line_id and line.sale_line_id.lot_id:
                line.write({'sale_lot_id': line.sale_line_id.lot_id.id})
        return records

    def write(self, vals):
        res = super(PurchaseOrderLine, self).write(vals)
        if 'sale_line_id' in vals:
            for line in self:
                if line.sale_line_id and line.sale_line_id.lot_id:
                    line.sale_lot_id = line.sale_line_id.lot_id
        return res


