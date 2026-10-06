from datetime import timedelta
from markupsafe import Markup
from odoo import api, fields, models, _


class JhSalesSubscriptionAdvice(models.Model):
    _name = 'jh.sales.subscription.advice'
    _description = 'Usuarios para avisos de suscripciones proximas a vencer'

    name = fields.Many2one('res.users', string='Usuarios', required=True, domain="[('share', '=', False)]")
    jh_email = fields.Char(string='Correo electronico', related='name.email', store=True, readonly=True)
    jh_active = fields.Boolean(string='Activo', default=True)
    jh_company_id = fields.Many2one('res.company', string='Compania', default=lambda self: self.env.company, required=True)
    jh_notify_type = fields.Selection([
        ('email', 'Correo electronico'), ('activity', 'Actividad interna'),
    ], string='Tipo de notificacion', default='email', required=True)

    _unique_user_company = models.Constraint(
        'UNIQUE(name, jh_company_id)', 'Este usuario ya esta registrado en esta compania.')

    @api.model
    def renovation_subscriptons_advice_cron(self):
        today = fields.Date.context_today(self)
        notifications = self.env['jh.subscription.renewal.notification']
        sent = 0
        for advice in self.search([('jh_active', '=', True)], order='id'):
            if advice.jh_company_id not in advice.name.company_ids:
                continue
            if advice.jh_notify_type == 'email' and not advice.jh_email:
                continue
            orders = self.env['sale.order'].with_user(advice.name).with_company(advice.jh_company_id).search([
                ('company_id', '=', advice.jh_company_id.id), ('state', '=', 'sale'),
                ('subscription_state', '=', '3_progress'),
                ('end_date', '>=', today), ('end_date', '<=', today + timedelta(days=60)),
                ('order_renove', '=', False),
            ], order='id')
            for order in orders:
                key = [('jh_advice_id', '=', advice.id), ('jh_order_id', '=', order.id),
                       ('jh_end_date', '=', order.end_date)]
                if notifications.search_count(key):
                    continue
                body = Markup('<p>%s: %s - %s (%s) <a href="%s">%s</a></p>') % (
                    _('Suscripcion proxima a vencer'), order.name,
                    order.partner_id.display_name, order.end_date,
                    order.get_base_url() + order.get_portal_url(), _('Ver pedido'))
                if advice.jh_notify_type == 'activity':
                    order.activity_schedule('mail.mail_activity_data_todo',
                        user_id=advice.name.id, summary=_('Revisar renovacion'),
                        note=body, date_deadline=order.end_date)
                else:
                    # Queue delivery; the mail cron owns transport and retries.
                    self.env['mail.mail'].create({
                        'subject': _('Suscripciones proximas a vencer'),
                        'body_html': body, 'email_to': advice.jh_email,
                    })
                notifications.create({
                    'jh_advice_id': advice.id, 'jh_order_id': order.id,
                    'jh_end_date': order.end_date,
                })
                sent += 1
            if self.env.context.get('cron_id') and not self.env['ir.cron']._commit_progress(1):
                break
        return sent


class JhSubscriptionRenewalNotification(models.Model):
    _name = 'jh.subscription.renewal.notification'
    _description = 'Registro de avisos de renovacion emitidos'
    _rec_name = 'jh_order_id'

    jh_advice_id = fields.Many2one('jh.sales.subscription.advice', required=True, ondelete='cascade',
        help='Configuracion del destinatario que recibio el aviso.\nDistingue los avisos de cada usuario y compania.')
    jh_order_id = fields.Many2one('sale.order', required=True, ondelete='cascade',
        help='Suscripcion incluida en el aviso de vencimiento.\nConserva una marca por destinatario y fecha de vencimiento.')
    jh_end_date = fields.Date(required=True,
        help='Fecha de vencimiento que motivo la notificacion.\nUn cambio de fecha permite emitir un nuevo aviso.')
    jh_company_id = fields.Many2one(related='jh_order_id.company_id', store=True,
        help='Compania de la suscripcion notificada.\nLimita el acceso a las companias permitidas al usuario.')

    _unique_notice = models.Constraint('UNIQUE(jh_advice_id, jh_order_id, jh_end_date)',
        'Ya existe un aviso para este destinatario, suscripcion y vencimiento.')
