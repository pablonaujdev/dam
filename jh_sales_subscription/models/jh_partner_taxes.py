from odoo import models, fields, api, _
from collections import defaultdict
from datetime import timedelta
from odoo.tools import frozendict

class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    jh_taxes_id = fields.Many2many('account.tax',
                                   'res_partner_sale_tax_rel',
                                   'partner_id', 'tax_id',
                                   string='Impuestos para Venta',
                                   domain=[('type_tax_use', '=', 'sale')])

    jh_purchase_taxes_id = fields.Many2many('account.tax',
                                            'res_partner_purchase_tax_rel',
                                            'partner_id', 'tax_id',
                                            string='Impuestos para Compra',
                                            domain=[('type_tax_use', '=', 'purchase')])

    jh_stock_picking_count = fields.Integer(string="Movimientos de stock", compute='_compute_stock_picking_count')

    def _compute_stock_picking_count(self):
        StockPicking = self.env['stock.picking']

        for partner in self:
            partner.jh_stock_picking_count = StockPicking.search_count(
                partner._get_stock_picking_domain()
            )

    def _get_stock_picking_domain(self):
        """
               Dominio base para buscar movimientos de stock asociados al contacto.

               Usamos commercial_partner_id para que, si el contacto pertenece a una empresa,
               también se puedan ver los movimientos relacionados con la empresa principal
               y sus direcciones/contactos hijos.

               """
        self.ensure_one()

        partner = self.commercial_partner_id or self

        return [
            ("partner_id", "child_of", partner.id),
        ]

    def action_view_stock_pickings(self):
        self.ensure_one()

        tree_view = self.env.ref(
            "jh_sales_subscription.view_stock_picking_partner_product_tree"
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Movimientos de stock - %s") % self.display_name,
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "views": [
                (tree_view.id, "list"),
                (False, "form"),
            ],
            "domain": self._get_stock_picking_domain(),
            "context": {
                "default_partner_id": self.id,
                "group_by": "picking_type_id",
            },
            "target": "current",
        }



class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'company_id', 'order_id.fiscal_position_id',
                 'order_id.partner_id.jh_taxes_id', 'order_id.partner_id.commercial_partner_id.jh_taxes_id')
    def _compute_tax_ids(self):
        super()._compute_tax_ids()
        for line in self:
            partner = line.order_id.partner_id
            taxes = partner.jh_taxes_id._filter_taxes_by_company(line.company_id)
            if not taxes:
                taxes = partner.commercial_partner_id.jh_taxes_id._filter_taxes_by_company(line.company_id)
            if taxes:
                line.tax_ids = line.order_id.fiscal_position_id.map_tax(taxes)


class PurchaseOrderLineInherit(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_id', 'company_id', 'order_id.fiscal_position_id',
                 'order_id.partner_id.jh_purchase_taxes_id',
                 'order_id.partner_id.commercial_partner_id.jh_purchase_taxes_id')
    def _compute_tax_id(self):
        super()._compute_tax_id()
        for line in self:
            partner = line.order_id.partner_id
            taxes = partner.jh_purchase_taxes_id._filter_taxes_by_company(line.company_id)
            if not taxes:
                taxes = partner.commercial_partner_id.jh_purchase_taxes_id._filter_taxes_by_company(line.company_id)
            if taxes:
                line.tax_ids = line.order_id.fiscal_position_id.map_tax(taxes)
