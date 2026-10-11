# -*- coding: utf-8 -*-
# Part of Avannubo. See LICENSE file for full copyright and licensing details.


from odoo import models, _
from odoo.exceptions import UserError

from .purchase_order_domain import sale_purchase_order_domain


class StockRule(models.Model):

    _inherit = 'stock.rule'


    def _make_po_get_domain(self, company_id, values, partner):
        domain = super()._make_po_get_domain(company_id, values, partner)
        if not partner.no_group_purchase:
            return domain

        sale_order = self.env['sale.order.line'].browse(values.get('sale_line_id')).order_id
        if not sale_order and values.get('reference_ids'):
            sale_order = values['reference_ids'].sale_ids
        if len(sale_order) > 1:
            raise UserError(_(
                "Cannot separate purchases for vendor %(vendor)s: the procurement references "
                "several sales orders without an originating sales line.", vendor=partner.display_name))
        if not sale_order:
            return domain

        return domain + sale_purchase_order_domain(sale_order.id)

