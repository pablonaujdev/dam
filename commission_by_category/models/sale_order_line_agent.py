# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class SaleOrderLineAgent(models.Model):

    _inherit = "sale.order.line.agent"



    @api.depends('agent_id', 'object_id.product_id.categ_id.commission_ids.commission_id',
                 'object_id.product_id.categ_id.commission_ids.agent_id')
    def _compute_commission_id(self):
        super()._compute_commission_id()
        for line in self:
            category_rule = line.object_id.product_id.categ_id.commission_ids.filtered(lambda rule: rule.agent_id == line.agent_id)[:1]
            if category_rule:
                line.commission_id = category_rule.commission_id
