# License AGPL-3.0 or later. Original customization: Avannubo.
from odoo import api, models
from . import report_sync


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('miac_reports_skip_sync'):
            return super().create(vals_list)
        pickings = self.env['stock.picking'].browse([vals['picking_id'] for vals in vals_list if vals.get('picking_id')])
        previous = report_sync.snapshot(pickings)
        moves = super().create(vals_list)
        report_sync.sync(pickings | moves.picking_id, previous)
        return moves

    def write(self, vals):
        if self.env.context.get('miac_reports_skip_sync') or not {'picking_id', 'sale_line_id', 'purchase_line_id'} & set(vals):
            return super().write(vals)
        pickings = self.picking_id | self.env['stock.picking'].browse(vals.get('picking_id') or [])
        previous = report_sync.snapshot(pickings)
        result = super().write(vals)
        report_sync.sync(pickings | self.picking_id, previous)
        return result

    def unlink(self):
        if self.env.context.get('miac_reports_skip_sync'):
            return super().unlink()
        pickings = self.picking_id
        previous = report_sync.snapshot(pickings)
        result = super().unlink()
        report_sync.sync(pickings, previous)
        return result
