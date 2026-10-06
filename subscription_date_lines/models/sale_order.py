# Part of Avannubo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partial_invoice = fields.Boolean(help="Conserva el indicador histórico de facturación parcial de V17.\nNo modifica las cantidades ni las fechas de facturación de Odoo 19.")
    # Client-side baselines also cover repeated header changes before saving.
    # Non-stored fields do not introduce columns or rewrite historical dates.
    date_subs_sync_start = fields.Date(compute='_compute_date_subs_sync_dates', readonly=False, help="Recuerda el inicio anterior durante la edición del contrato.\nReferencia transitoria para conservar fechas particulares de las líneas.")
    date_subs_sync_end = fields.Date(compute='_compute_date_subs_sync_dates', readonly=False, help="Recuerda el fin anterior durante la edición del contrato.\nReferencia transitoria para conservar fechas particulares de las líneas.")
    date_subs_suggested_plan_id = fields.Many2one('sale.subscription.plan', store=False, help="Identifica el plan sugerido en la edición actual del pedido.\nReferencia no almacenada para advertir de productos con planes distintos.")

    def _compute_date_subs_sync_dates(self):
        for order in self:
            order.date_subs_sync_start = order.start_date
            order.date_subs_sync_end = order.end_date

    def _date_subs_default_plans(self):
        self.ensure_one()
        lines = self.order_line.filtered(lambda line: line.recurring_invoice and not line.display_type)
        return lines.product_id.subscription_plan_default

    def _date_subs_can_suggest_plan(self):
        self.ensure_one()
        lines = self.order_line.filtered(lambda line: line.recurring_invoice and not line.display_type)
        # No plan is required when all recurring products permit a one-time sale.
        return bool(lines) and (self.is_subscription or not all(lines.product_id.mapped('allow_one_time_sale')))

    def _date_subs_apply_default_plan(self):
        if self.env.context.get('date_subs_skip_plan'):
            return
        for order in self:
            if order.state not in ('draft', 'sent') or order.plan_id:
                continue
            if order.sale_order_template_id.plan_id:
                order.plan_id = order.sale_order_template_id.plan_id
            elif order._date_subs_can_suggest_plan():
                plans = order._date_subs_default_plans()
                if len(plans) == 1:
                    order.plan_id = plans

    @api.onchange('order_line', 'sale_order_template_id')
    def onchage_plan_subscription_product(self):
        for order in self:
            plans = order._date_subs_default_plans()
            if order.plan_id and order.plan_id != order.date_subs_suggested_plan_id:
                continue
            if order.sale_order_template_id.plan_id:
                order.plan_id = order.sale_order_template_id.plan_id
                order.date_subs_suggested_plan_id = False
            elif order._date_subs_can_suggest_plan() and len(plans) > 1:
                order.plan_id = False
                order.date_subs_suggested_plan_id = False
                return {'warning': {
                    'title': _('Different recurring plans'),
                    'message': _('The recurring products have different default plans. Select the contract plan manually.'),
                }}
            elif not order.plan_id and order._date_subs_can_suggest_plan() and len(plans) == 1:
                order.plan_id = plans
                order.date_subs_suggested_plan_id = plans

    @api.onchange('plan_id')
    def _onchange_date_subs_plan_selection(self):
        if self.plan_id != self.date_subs_suggested_plan_id:
            self.date_subs_suggested_plan_id = False

    @api.onchange('start_date', 'end_date')
    def _onchange_date_subs_contract_dates(self):
        for order in self:
            for header, line_field, baseline in (
                ('start_date', 'date_subs_start', 'date_subs_sync_start'),
                ('end_date', 'date_subs_end', 'date_subs_sync_end'),
            ):
                previous = order[baseline]
                if previous != order[header]:
                    for line in order.order_line.filtered(lambda item: item.recurring_invoice and not item.display_type):
                        if not line[line_field] or line[line_field] == previous:
                            line[line_field] = order[header]
                order[baseline] = order[header]

    @api.model_create_multi
    def create(self, vals_list):
        # Process all lines before choosing a plan, never the first line alone.
        orders = super(SaleOrder, self.with_context(date_subs_skip_plan=True)).create(vals_list)
        orders = orders.with_env(self.env)
        for order, vals in zip(orders, vals_list):
            if 'plan_id' not in vals:
                order._date_subs_apply_default_plan()
        return orders

    def write(self, vals):
        changed_dates = {
            header: line_field for header, line_field in
            (('start_date', 'date_subs_start'), ('end_date', 'date_subs_end'))
            if header in vals
        }
        previous = {}
        for order in self:
            previous[order.id] = {
                header: (order[header], {line.id: line[line_field] for line in order.order_line})
                for header, line_field in changed_dates.items()
            }
        explicit_dates = {}
        for command in vals.get('order_line', []):
            if command[0] == fields.Command.UPDATE:
                explicit_dates.setdefault(command[1], set()).update(command[2])
        result = super(SaleOrder, self.with_context(date_subs_skip_plan=True)).write(vals)
        for order in self:
            for header, line_field in changed_dates.items():
                old_header, old_lines = previous[order.id][header]
                lines = order.order_line.filtered(lambda line: (
                    line.recurring_invoice and not line.display_type
                    and line.id in old_lines
                    and line_field not in explicit_dates.get(line.id, set())
                    and (not old_lines[line.id] or old_lines[line.id] == old_header)
                    and line[line_field] != order[header]
                ))
                lines.write({line_field: order[header]})
        if 'order_line' in vals and 'plan_id' not in vals:
            self._date_subs_apply_default_plan()
        return result
