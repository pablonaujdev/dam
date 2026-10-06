# Part of Avannubo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    subscription_plan_default = fields.Many2one('sale.subscription.plan', string='Recurrence default', help="Propone el plan recurrente al añadir este producto a un pedido sin plan.\nCon planes predeterminados distintos, el usuario debe seleccionar el plan del contrato.")
