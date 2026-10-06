# Part of Avannubo. License AGPL-3.

from datetime import timedelta

from odoo import fields, models, _
from odoo.tools import format_date
from odoo.addons.sale_subscription.models.sale_order import SUBSCRIPTION_PROGRESS_STATE


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        # Capture planned dates before stock recomputes dates during completion.
        pending = self.filtered(lambda picking: picking.state not in ('done', 'cancel')
                                and picking.picking_type_id.code == 'outgoing')
        planned = {picking.id: picking.scheduled_date for picking in pending}
        result = super()._action_done()
        completed = pending.filtered(lambda picking: picking.state == 'done' and planned[picking.id])
        for picking in completed.sorted(lambda picking: (planned[picking.id], picking.id)):
            picking._activation_update_contracts(planned[picking.id])
        return result

    def _activation_update_contracts(self, planned_date):
        self.ensure_one()
        if not planned_date:
            return
        moves = self.move_ids.filtered(lambda move: (
            move.state == 'done' and move.quantity > 0 and move.sale_line_id
            and move.location_dest_id.usage == 'customer'
            and move.location_id.usage != 'customer'
        ))
        calendar_tz = self.company_id.resource_calendar_id.tz or 'UTC'
        planned_day = fields.Datetime.context_timestamp(self.with_context(tz=calendar_tz), planned_date).date()
        orders = moves.sale_line_id.order_id.filtered(lambda order: (
            order.state == 'sale' and order.is_subscription and order.plan_id
            and order.subscription_state in SUBSCRIPTION_PROGRESS_STATE
        ))
        for order in orders:
            order_moves = moves.filtered(lambda move: move.sale_line_id.order_id == order)
            days = max(order_moves.product_id.mapped('days_to_activate'))
            start = planned_day + timedelta(days=days)
            values = {'start_date': start, 'next_invoice_date': start,
                      'end_date': start + order.plan_id.billing_period}
            previous = {name: order[name] for name in values}
            if all(previous[name] == value for name, value in values.items()):
                continue
            # One write retains native validations and line-date synchronization.
            order.write(values)
            order.message_post(body=_(
                'Delivery %(delivery)s recalculated subscription dates from its planned date. '
                'Start: %(old_start)s → %(start)s. Next invoice: %(old_invoice)s → %(invoice)s. '
                'End: %(old_end)s → %(end)s.',
                delivery=self.display_name,
                old_start=format_date(self.env, previous['start_date']) if previous['start_date'] else '-',
                start=format_date(self.env, start),
                old_invoice=format_date(self.env, previous['next_invoice_date']) if previous['next_invoice_date'] else '-',
                invoice=format_date(self.env, start),
                old_end=format_date(self.env, previous['end_date']) if previous['end_date'] else '-',
                end=format_date(self.env, values['end_date']),
            ))
