# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta

class SaleOrder(models.Model):

    _inherit = 'sale.order'

    order_renove = fields.Many2one('sale.order', 'Order Renove', readonly=True)
    cancelation_reason = fields.Char(string='Cancelation Reason', readonly=True)

    def action_cancel(self):
        is_renovation = self.search([('order_renove','in',self.ids)])
        if not is_renovation or self.env.context.get('cancel_renovation',False):
            return super(SaleOrder, self).action_cancel()
        else:
            wiz_id = self.env['sale.order.cancel.wiz'].create({
                'order_ids': [(6, 0, self.ids)]
            })
            action = {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'name': _('Order Cancelation'),
                'res_model': 'sale.order.cancel.wiz',
                'target': 'new',
                'context': self.env.context,
                'res_id': wiz_id.id,
            }
            return action

    @api.model
    def renovation_subscriptons_cron(self):
        processed = 0
        today = fields.Date.context_today(self)
        for company in self.env.companies:
            limit_date = today + relativedelta(months=max(company.months_renovation, 0))
            domain = [('company_id', '=', company.id), ('state', '=', 'sale'),
                      ('subscription_state', '=', '3_progress'), ('end_date', '!=', False),
                      ('end_date', '<=', limit_date), ('order_renove', '=', False)]
            while orders := self.with_company(company).search(domain, order='id', limit=100):
                for order in orders:
                    existing = self.search([('subscription_id', '=', order.id),
                        ('subscription_state', '=', '2_renewal'), ('state', '!=', 'cancel')], limit=1)
                    if existing:
                        order.order_renove = existing
                    else:
                        values = order.with_context(renewal_pricing_mode='keep_current')._prepare_upsell_renew_order_values('2_renewal')
                        start = order.end_date + relativedelta(days=1)
                        values.update(date_order=start, start_date=start, next_invoice_date=start)
                        renewal = self.with_company(company).create(values)
                        units = {'day': 'days', 'week': 'weeks', 'month': 'months', 'year': 'years'}
                        unit = units.get(renewal.plan_id.billing_period_unit)
                        if unit:
                            renewal.end_date = start + relativedelta(**{unit: renewal.plan_id.billing_period_value})
                        order.order_renove = renewal
                    processed += 1
                if self.env.context.get('cron_id') and not self.env['ir.cron']._commit_progress(len(orders)):
                    return processed
        return processed








    def _prepare_upsell_renew_order_values(self, subscription_state):
        values = super()._prepare_upsell_renew_order_values(subscription_state)
        originals = {line.id: line for line in self.order_line}
        for command in values.get('order_line', []):
            if command[0] != 0:
                continue
            original = originals.get(command[2].get('parent_line_id'))
            if original and not original.display_type:
                command[2]['lot_id'] = original.lot_id.id
                command[2]['discount'] = original.discount
        return values
