# -*- coding: utf-8 -*-

from odoo import fields, models, _, api
from odoo.exceptions import ValidationError



class LinkMachineWiz(models.TransientModel):

    _name = "link.machine.wiz"
    _description = "Link Machine Wiz"

    sale_line_id = fields.Many2one('sale.order.line', string='Line', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    sale_linked_id = fields.Many2one('sale.order.line', string='Product to link', domain=[('lot_id','!=',False),('main_line_id','=',False)])

    is_new = fields.Boolean(string="Is new", default=False)
    lot_name = fields.Char(string="Lot")
    product_id = fields.Many2one('product.product', string='Product')

    is_external = fields.Boolean(string="Is external", default=False)
    lot_id = fields.Many2one('stock.lot', string='Lot')

    @api.onchange('is_new')
    def onchange_is_new(self):
        if self.is_new:
            self.is_external = False
            self.product_id = self.env['product.product'].search([('default_for_lot','=',True)], limit=1)

    @api.onchange('is_external')
    def onchange_is_external(self):
        if self.is_external:
            self.is_new = False

    def action_confirm(self):
        if not self.sale_linked_id and not self.is_new and not self.is_external:
            raise ValidationError(_('The Product to link is need'))
        if self.sale_linked_id.partner_id != self.partner_id and not self.is_new and not self.is_external:
            raise ValidationError(_('The Partner is not the same.'))
        if not self.product_id and self.is_new:
            raise ValidationError(_('The Product to link is need.'))
        if not self.lot_name and self.is_new:
            raise ValidationError(_('The Lot to link is need.'))
        if not self.lot_id and self.is_external:
            raise ValidationError(_('The Lot to link is need.'))

        if not self.is_new and not self.is_external:
            self.sale_line_id.write({
                'main_line_id': self.sale_linked_id.id,
                'lot_id': self.sale_linked_id.lot_id.id,
            })
        elif self.is_external:
            self.sale_line_id.write({
                'main_line_id': self.sale_line_id.id,
                'lot_id': self.lot_id.id,
            })
        else:
            lot_id = self.env['stock.lot'].create({
                'name': self.lot_name,
                'product_id': self.product_id.id,
            })
            self.sale_line_id.write({
                'main_line_id': self.sale_line_id.id,
                'lot_id': lot_id.id,
            })





