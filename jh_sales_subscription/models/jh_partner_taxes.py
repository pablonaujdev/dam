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
            "view_mode": "tree,form",
            "views": [
                (tree_view.id, "tree"),
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

    # Pricing fields - Campo Original para Heredar el Compute
    tax_id = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        compute='_compute_tax_id',
        store=True, readonly=False, precompute=True,
        context={'active_test': False},
        check_company=True)

    @api.depends('product_id', 'company_id', 'order_id.partner_id', 'order_id.fiscal_position_id')
    def _compute_tax_id(self):
        lines_by_company = defaultdict(lambda: self.env['sale.order.line'])
        cached_taxes = {}

        for line in self:
            lines_by_company[line.company_id] += line

        for company, lines in lines_by_company.items():
            for line in lines.with_company(company):
                taxes = None

                # PRIORIDAD 1: impuestos definidos en el cliente (contacto o empresa)
                partner = line.order_id.partner_id if line.order_id else False
                if partner:
                    taxes = partner.jh_taxes_id.filtered(lambda t: t.company_id == company)
                    # Si el contacto no tiene, usar impuestos de la empresa (commercial_partner)
                    if not taxes and partner.commercial_partner_id and partner.commercial_partner_id != partner:
                        taxes = partner.commercial_partner_id.jh_taxes_id.filtered(lambda t: t.company_id == company)

                # PRIORIDAD 2: solo si el cliente no tiene nada parametrizado, usar impuestos del producto
                if not taxes and line.product_id:
                    taxes = line.product_id.taxes_id.filtered(lambda t: t.company_id == company)

                if not taxes:
                    line.tax_id = False
                    continue

                fiscal_position = line.order_id.fiscal_position_id
                cache_key = (fiscal_position.id, company.id, tuple(taxes.ids))
                cache_key += line._get_custom_compute_tax_cache_key()

                if cache_key in cached_taxes:
                    result = cached_taxes[cache_key]
                else:
                    result = fiscal_position.map_tax(taxes)
                    cached_taxes[cache_key] = result

                line.tax_id = result

class PurchaseOrderLineInherit(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_id', 'partner_id')
    def _compute_tax_id(self):
        for record in self:

            tax_partner = record.order_id.partner_id.jh_purchase_taxes_id

            if tax_partner:
                record.taxes_id = tax_partner
            else:
                super()._compute_tax_id()

