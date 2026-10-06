# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    commission_ids = fields.One2many(
        comodel_name='product.category.agent.commission',
        inverse_name='categ_id',
        string="Commissions",
        copy=True,
        help='Relaciona las comisiones por categoria con sus agentes.\nSe utiliza cuando no existe una comision manual en la linea.')
