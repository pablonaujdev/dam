# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    sale_lot_id = fields.Char(compute='_compute_sale_lot_id', store=True,
        string='Lot/Serial Number', readonly=True, copy=False,
        help="Lot/Serial Number of the product to unbuild.")

    @api.depends('sale_line_ids', 'sale_line_ids.lot_id', 'sale_line_ids.lot_id.name')
    def _compute_sale_lot_id(self):
        for line in self:
            lot_names = [name for name in line.sale_line_ids.mapped('lot_id.name') if name]
            line.sale_lot_id = ', '.join(lot_names)


