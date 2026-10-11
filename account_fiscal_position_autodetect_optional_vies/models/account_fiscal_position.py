# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    vat_vies_required = fields.Boolean(
        string="Vat was VIES validated",
        help=("Separates automatic fiscal positions by the commercial partner's stored VIES result.\n"
              "Checked matches valid VIES; unchecked matches non-valid VIES and keeps company VAT checks."),
    )

    def _get_fpos_validation_functions(self, partner):
        validations = super()._get_fpos_validation_functions(partner)
        vies_valid = partner.commercial_partner_id.vies_valid
        return validations + [
            lambda fiscal_position: fiscal_position.vat_vies_required == vies_valid,
        ]
