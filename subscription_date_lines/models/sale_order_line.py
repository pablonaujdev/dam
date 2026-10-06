# Part of Avannubo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    date_subs_start = fields.Date(string="Date Start", copy=False, help="Indica el inicio particular de la suscripción de esta línea.\nPermite seguimiento independiente sin modificar la facturación nativa.")
    date_subs_end = fields.Date(string="Date End", copy=False, help="Indica el fin particular de la suscripción de esta línea.\nLas fechas negociadas se conservan al cambiar las fechas del contrato.")

    def _date_subs_missing_dates(self, explicit_values):
        self.ensure_one()
        values = {}
        if self.recurring_invoice and not self.display_type and self.order_id:
            for name, header in (('date_subs_start', 'start_date'), ('date_subs_end', 'end_date')):
                if name not in explicit_values and not self[name] and self.order_id[header]:
                    values[name] = self.order_id[header]
        return values

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line, vals in zip(lines, vals_list):
            dates = line._date_subs_missing_dates(vals)
            if dates:
                line.write(dates)
        lines.order_id._date_subs_apply_default_plan()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if 'product_id' in vals or 'order_id' in vals:
            for line in self:
                dates = line._date_subs_missing_dates(vals)
                if dates:
                    line.write(dates)
            self.order_id._date_subs_apply_default_plan()
        return result

    @api.onchange('product_id', 'order_id')
    def _onchange_date_subs_product_order(self):
        for line in self:
            line.update(line._date_subs_missing_dates({}))
