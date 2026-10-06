# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    commission_category_ids = fields.One2many(
        comodel_name='product.category.agent.commission',
        inverse_name='agent_id',
        string="Category Commissions",
        copy=True,
        help='Relaciona las comisiones por categoria con sus agentes.\nSe utiliza cuando no existe una comision manual en la linea.')
