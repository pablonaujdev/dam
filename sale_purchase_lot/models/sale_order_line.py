# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.fields import Domain
from odoo.tools import float_compare, float_round, float_repr


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    main_line_id = fields.Many2one('sale.order.line', string='Complement for', readonly=True)

    lot_id = fields.Many2one(
        'stock.lot', 'Lot Serial Number', copy=False,
        help="Lot Serial Number of the product to unbuild.")
    partner_id = fields.Many2one(related='order_id.partner_id', store=True)


    def write(self, vals):
        returned = super(SaleOrderLine, self).write(vals)
        if 'lot_id' in vals:
            purchaseLineObj = self.env['purchase.order.line']
            for line in self:
                purchase_lines = purchaseLineObj.search([('sale_line_id','=',line.id)])
                if line.lot_id and purchase_lines:
                    purchase_lines.write({'sale_lot_id': line.lot_id.id})
                elif purchase_lines:
                    purchase_lines.write({'sale_lot_id': False})
                optional_lines = line.order_id.order_line.filtered(lambda l: l.main_line_id == line and l.id != line.id)
                if optional_lines and line.lot_id:
                    optional_lines.write({'lot_id': line.lot_id.id})
                elif optional_lines:
                    optional_lines.write({'lot_id': False})
        return returned

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        by_parent = {(line.order_id.id, line.parent_line_id.id): line for line in lines if 'parent_line_id' in line._fields and line.parent_line_id}
        for line in lines:
            if 'parent_line_id' in line._fields and line.parent_line_id:
                parent = line.parent_line_id
                if parent.main_line_id:
                    line.main_line_id = by_parent.get((line.order_id.id, parent.main_line_id.id), parent.main_line_id)
                continue
            candidates = line.order_id.order_line.filtered(
                lambda item: item != line and not item.main_line_id
                and line.product_id.product_tmpl_id in item.product_id.product_tmpl_id.optional_product_ids)
            used = line.order_id.order_line.filtered(lambda item: item != line and item.product_id == line.product_id).main_line_id
            candidate = (candidates - used)[:1]
            if candidate:
                line.main_line_id = candidate
        return lines

    @api.depends('order_id.name', 'partner_id.name', 'product_id.name', 'lot_id.name')
    @api.depends_context('name_lot')
    def _compute_display_name(self):
        if self.env.context.get('name_lot'):
            for line in self:
                line.display_name = '[%s-%s] %s (%s)' % (
                    line.order_id.name or '', line.partner_id.name or '',
                    line.product_id.name or '', line.lot_id.name or '')
        else:
            super()._compute_display_name()


    def link_to_machine(self):
        if not self.main_line_id:
            linker = self.env['link.machine.wiz'].create({
                'sale_line_id': self.id,
                'partner_id': self.order_id.partner_id.id
            })
        elif self.main_line_id.id != self.id:
            linker = self.env['link.machine.wiz'].create({
                'sale_line_id': self.id,
                'partner_id': self.order_id.partner_id.id,
                'sale_linked_id': self.main_line_id.id or False
            })
        elif self.main_line_id.id == self.id and self.lot_id:
            linker = self.env['link.machine.wiz'].create({
                'sale_line_id': self.id,
                'partner_id': self.order_id.partner_id.id,
                'is_external': True,
                'lot_id': self.lot_id.id
            })
        else:
            linker = self.env['link.machine.wiz'].create({
                'sale_line_id': self.id,
                'partner_id': self.order_id.partner_id.id
            })
        ctx = self.env.context.copy()
        ctx.update({'sale_line_id': self.id, 'name_lot': True})
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'name': 'Link',
            'res_model': 'link.machine.wiz',
            'res_id': linker.id,
            'target': 'new',
            'context': ctx
        }

        return action




    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if value and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            return Domain.OR([domain, Domain('lot_id.name', operator, value), Domain('partner_id.name', operator, value)])
        return domain


