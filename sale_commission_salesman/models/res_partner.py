# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, exceptions, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    salesman_as_agent = fields.Boolean(
        string="Convert salesman into agent",
        help="Utiliza el contacto del vendedor como agente si el cliente no aporta agentes.\nRequiere agente y comisión; cambiar el vendedor no regenera comisiones existentes.",
    )

    @api.constrains("salesman_as_agent", "commission_id")
    def _check_salesman_as_agent(self):
        for record in self:
            if record.salesman_as_agent and not record.commission_id:
                raise exceptions.ValidationError(
                    _("You can't have a salesman auto-agent without commission.")
                )
