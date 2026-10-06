# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    days_to_activate = fields.Integer(string='Days to Active', default=3, help="Añade días naturales a la fecha prevista de entrega para activar el contrato.\nSe hereda de la categoría salvo valor explícito; cada entrega vuelve a ajustar las fechas.")

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(['categ_id', 'days_to_activate'])
        values_list = []
        for vals in vals_list:
            values = dict(vals)
            if 'days_to_activate' not in values:
                if 'default_days_to_activate' in self.env.context:
                    values['days_to_activate'] = defaults['days_to_activate']
                else:
                    category = self.env['product.category'].browse(values.get('categ_id', defaults.get('categ_id')))
                    if category:
                        values['days_to_activate'] = category.days_to_activate
            values_list.append(values)
        return super().create(values_list)

    def write(self, vals):
        values = dict(vals)
        if values.get('categ_id') and 'days_to_activate' not in values:
            values['days_to_activate'] = self.env['product.category'].browse(values['categ_id']).days_to_activate
        return super().write(values)

    @api.onchange('categ_id')
    def onchange_categ_for_active(self):
        for template in self:
            if template.categ_id:
                template.days_to_activate = template.categ_id.days_to_activate


