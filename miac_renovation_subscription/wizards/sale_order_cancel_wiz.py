# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError



class SaleOrderCancelWiz(models.TransientModel):

    _name = "sale.order.cancel.wiz"
    _description = "Sale Order Cancel Wiz"

    reason = fields.Char(string="Reason")
    order_ids = fields.Many2many('sale.order', relation='sale_order_cancelation_reason_wiz_rel', string='Orders')


    def accept_reason(self):
        if not self.reason:
            raise ValidationError(_("The reason is required."))

        self.order_ids.write({'cancelation_reason': self.reason})
        self.order_ids.with_context(cancel_renovation=True).action_cancel()






