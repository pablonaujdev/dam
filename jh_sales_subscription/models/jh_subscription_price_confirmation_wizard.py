from odoo import api, fields, models, _


class JhSubscriptionPriceConfirmationWizard(models.TransientModel):
    _name = 'jh.subscription.price.confirmation.wizard'
    _description = 'Confirmacion de precios para renovacion de suscripciones'

    order_id = fields.Many2one('sale.order', required=True, readonly=True)
    subscription_state = fields.Selection(
        selection=[
            ('2_renewal', 'Renew'),
            ('7_upsell', 'Upsell'),
        ],
        required=True,
        readonly=True,
    )
    title = fields.Char(readonly=True)
    message = fields.Text(readonly=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        subscription_state = self.env.context.get('default_subscription_state', '2_renewal')
        is_renewal = subscription_state == '2_renewal'
        values.setdefault('title', _('Actualizar precios de la renovación') if is_renewal else _('Actualizar precios del upsell'))
        values.setdefault(
            'message',
            _(
                'Se detectaron lineas con condiciones comerciales diferentes a la tarifa vigente. '
                'Puede actualizar a la tarifa actual o mantener el precio y descuento existentes.'
            ),
        )
        return values

    def action_keep_current_conditions(self):
        self.ensure_one()
        return self.order_id.with_context(
            skip_renewal_price_confirmation=True,
            renewal_pricing_mode='keep_current',
        )._jh_prepare_subscription_order_with_mode(self.subscription_state)

    def action_update_tariff(self):
        self.ensure_one()
        return self.order_id.with_context(
            skip_renewal_price_confirmation=True,
            renewal_pricing_mode='update_tariff',
        )._jh_prepare_subscription_order_with_mode(self.subscription_state)
