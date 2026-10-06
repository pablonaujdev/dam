# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_agents_vals_partner(self, partner, settlement_type=None):
        self.ensure_one()
        values = super()._prepare_agents_vals_partner(partner, settlement_type)
        if (values or self.move_id.move_type not in ("out_invoice", "out_refund")
                or not self.product_id or self.display_type != "product" or self.commission_free):
            return values
        salesman = self.move_id.invoice_user_id.partner_id
        if salesman.agent and salesman.salesman_as_agent and salesman.commission_id:
            return [Command.create(self._prepare_agent_vals(salesman))]
        return values
