# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools import float_compare, float_round, float_repr


class StockMoveLine(models.Model):

    _inherit = 'stock.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for line in records:
            if line.move_id and line.lot_id and line.move_id.sale_line_id and line.move_id.sale_line_id and line.lot_id:
                line.move_id.sale_line_id.lot_id = line.lot_id
                purchase_lines = self.env['purchase.order.line'].search([('sale_line_id', '=', line.move_id.sale_line_id.id)])
                if line.lot_id and purchase_lines:
                    purchase_lines.write({'sale_lot_id': line.lot_id.id})
        return records

    def write(self, vals):
        returned = super(StockMoveLine, self).write(vals)
        if 'move_id' in vals or 'lot_id' in vals:
            purchaseLineObj = self.env['purchase.order.line']
            for line in self:
                if line.move_id and line.lot_id and line.move_id.sale_line_id and line.move_id.sale_line_id and line.lot_id:
                    line.move_id.sale_line_id.lot_id = line.lot_id
                    purchase_lines = purchaseLineObj.search([('sale_line_id', '=', line.move_id.sale_line_id.id)])
                    if line.lot_id and purchase_lines:
                        purchase_lines.write({'sale_lot_id': line.lot_id.id})
                    elif purchase_lines:
                        purchase_lines.write({'sale_lot_id': False})
        return returned

    def unlink(self):
        purchaseLineObj = self.env['purchase.order.line']
        for line in self:
            if line.move_id and line.lot_id and line.move_id.sale_line_id and line.move_id.sale_line_id and line.lot_id:
                line.move_id.sale_line_id.lot_id = False
                purchase_lines = purchaseLineObj.search([('sale_line_id', '=', line.move_id.sale_line_id.id)])
                if purchase_lines:
                    purchase_lines.write({'sale_lot_id': False})
        return super(StockMoveLine, self).unlink()





