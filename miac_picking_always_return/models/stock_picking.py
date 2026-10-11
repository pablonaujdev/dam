# Part of Avannubo. License AGPL-3.
from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _can_return(self):
        self.check_access('read')
        can_return = super()._can_return()
        if self.state in ('draft', 'cancel'):
            return False
        return can_return or self.state in ('confirmed', 'waiting', 'assigned')
