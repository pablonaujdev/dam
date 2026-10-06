# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ProductCategory(models.Model):

    _inherit = 'product.category'

    days_to_activate = fields.Integer(string='Days to Active', default=3, help="Establece los días naturales para activar suscripciones desde la fecha prevista de entrega.\nCambiar este valor reemplaza los días de todos los productos accesibles de esta categoría.")

    def write(self, vals):
        returned = super(ProductCategory, self).write(vals)
        if 'days_to_activate' in vals:
            productObj = self.env['product.template'].with_context(active_test=False)
            templates = productObj.search([('categ_id', 'in', self.ids)])
            if templates:
                templates.write({'days_to_activate': vals['days_to_activate']})
        return returned





