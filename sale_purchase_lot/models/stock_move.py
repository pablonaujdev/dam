# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools import float_compare, float_round, float_repr


class StockMove(models.Model):

    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for move in records:
            if move.sale_line_id and move.lot_ids:
                move.sale_line_id.lot_id = move.lot_ids[0]
        return records

    def write(self, vals):
        returned = super(StockMove, self).write(vals)
        if 'sale_line_id' in vals or 'lot_ids' in vals:
            for move in self:
                if move.sale_line_id and move.sale_line_id and move.lot_ids:
                    move.sale_line_id.lot_id = move.lot_ids[0]
        return returned





