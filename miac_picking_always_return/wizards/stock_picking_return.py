# Part of Avannubo. License AGPL-3.
from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPickingReturn(models.TransientModel):
    _inherit = 'stock.return.picking'

    # Native stored computes otherwise run as superuser when filling the wizard.
    product_return_moves = fields.One2many(compute_sudo=False, help='Lists the original moves eligible for the return with quantities initially at zero.\nEnter quantities or use Return All; access follows the current user and company.')

    def _create_return(self):
        self.ensure_one()
        if self.picking_id and not self.picking_id._can_return():
            raise UserError(_(
                'This transfer no longer allows a return. '
                'Only confirmed, waiting, ready or done transfers can be returned.'
            ))
        return super()._create_return()
