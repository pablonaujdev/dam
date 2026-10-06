# Copyright 2014-2020 Akretion - Alexis de Lattre
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_mode_id = fields.Many2one(
        comodel_name="account.payment.mode",
        compute="_compute_payment_mode",
        store=True,
        readonly=False,
        precompute=True,
        check_company=True,
        domain="[('payment_type', '=', 'inbound'), ('company_id', '=', company_id)]",
        help="Selecciona el modo OCA de cobro del pedido.\nSe traslada a la factura y separa pedidos con modos de pago distintos.",
    )

    @api.depends("partner_id", "company_id", "partner_id.customer_payment_mode_id")
    def _compute_payment_mode(self):
        for order in self:
            if order.partner_id:
                mode = order.partner_id.with_company(order.company_id).customer_payment_mode_id
                order.payment_mode_id = mode if mode.company_id == order.company_id else False
            else:
                order.payment_mode_id = False

    def _get_payment_mode_vals(self, vals):
        vals["payment_mode_id"] = self.payment_mode_id.id or False

    def _prepare_invoice(self):
        """Propagate the mode; OCA account computes the invoice bank."""
        vals = super()._prepare_invoice()
        self._get_payment_mode_vals(vals)
        return vals

    @api.model
    def _get_invoice_grouping_keys(self) -> list:
        """
        When several sale orders are generating invoices,
        we want to add the payment mode in grouping criteria.
        """
        keys = super()._get_invoice_grouping_keys()
        if "payment_mode_id" not in keys:
            keys.append("payment_mode_id")
        return keys
