# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, models


class SaleOrdeLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_agents_vals_partner(self, partner, settlement_type=None):
        """Use the preparation hook shared by OCA and the MIAC/JH compute."""
        self.ensure_one()
        values = super()._prepare_agents_vals_partner(partner, settlement_type)
        if values or not self.product_id or self.display_type or self.commission_free:
            return values
        salesman = self.order_id.user_id.partner_id
        if salesman.agent and salesman.salesman_as_agent and salesman.commission_id:
            return [Command.create(self._prepare_agent_vals(salesman))]
        return values
