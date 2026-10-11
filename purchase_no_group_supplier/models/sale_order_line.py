# -*- coding: utf-8 -*-
# Part of Avannubo. See LICENSE file for full copyright and licensing details.


from odoo import models

from .purchase_order_domain import sale_purchase_order_domain


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    def _get_additional_domain_for_purchase_order_line(self):
        domain = super()._get_additional_domain_for_purchase_order_line()
        if self._purchase_service_match_supplier().partner_id.no_group_purchase:
            domain = list(domain) + [
                ('order_id', 'any', sale_purchase_order_domain(self.order_id.id)),
            ]
        return domain

    def _purchase_service_create(self, quantity=False):
        grouped_lines = {}
        native_lines = self.env['sale.order.line']
        for line in self:
            company = line._purchase_service_get_company()
            supplier = line.with_company(company)._purchase_service_match_supplier()
            if supplier.partner_id.no_group_purchase:
                key = (company.id, line.order_id.id)
                grouped_lines.setdefault(key, self.env['sale.order.line'])
                grouped_lines[key] |= line
            else:
                native_lines |= line

        result = {}
        if native_lines:
            result.update(super(SaleOrderLine, native_lines)._purchase_service_create(quantity=quantity))
        for lines in grouped_lines.values():
            result.update(super(SaleOrderLine, lines)._purchase_service_create(quantity=quantity))
        return result
