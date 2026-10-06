# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    jh_delivery_subscription_count = fields.Integer(
        string='Suscripciones activas en esta dirección',
        compute='_compute_jh_delivery_subscription_count',
        help=(
            'Cuenta las suscripciones en curso enviadas a esta dirección de entrega.\n'
            'Se muestra en el contacto y en sus tarjetas kanban a los usuarios de ventas.'
        ),
    )

    def _compute_jh_delivery_subscription_count(self):
        counts = {partner.id: 0 for partner in self}
        delivery_partners = self.filtered(lambda partner: partner.type == 'delivery')
        if delivery_partners and self.env.user.has_group('sales_team.group_sale_salesman'):
            subscription_data = self.env['sale.order']._read_group(
                domain=[
                    ('partner_shipping_id', 'in', delivery_partners.ids),
                    ('is_subscription', '=', True),
                    ('state', '=', 'sale'),
                    ('subscription_state', '=', '3_progress'),
                ],
                groupby=['partner_shipping_id'],
                aggregates=['__count'],
            )
            for partner, count in subscription_data:
                counts[partner.id] = count
        for partner in self:
            partner.jh_delivery_subscription_count = counts[partner.id]

    def action_view_jh_delivery_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Suscripciones en esta dirección'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('sale_subscription.sale_subscription_view_tree').id, 'list'),
                (self.env.ref('sale_subscription.sale_subscription_primary_form_view').id, 'form'),
            ],
            'domain': [
                ('partner_shipping_id', '=', self.id),
                ('is_subscription', '=', True),
                ('state', '=', 'sale'),
                ('subscription_state', '=', '3_progress'),
            ],
        }
