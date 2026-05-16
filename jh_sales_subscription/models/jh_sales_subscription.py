from odoo import models, fields, api, _
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class jh_sales_subscription_advice(models.Model):
    _name ='jh.sales.subscription.advice'
    _description = 'Usuarios para automatica de suscripciones proximas a vencer'

    name = fields.Many2one('res.users', string= 'Usuarios', required=True, domain="[('share', '=', False)]")
    jh_email = fields.Char(string='Correo electrónico', related='name.email', store=True, readonly=True)
    jh_active = fields.Boolean(string='Activo', default=True)
    jh_company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    jh_notify_type = fields.Selection([
        ('email', 'Correo electrónico'),
        ('activity', 'Actividad interna'),
    ], string='Tipo de notificación', default='email')

    _sql_constraints = [
        ('unique_user_company', 'UNIQUE(name, jh_company_id)', 'Este usuario ya está registrado en esta compañía.')
    ]

    def renovation_subscriptons_advice_cron(self):
        saleObj = self.env['sale.order']
        companies = self.env['res.company'].search([])

        today = datetime.today()
        start_date = today
        end_date = today + timedelta(days=60)

        for company in companies:
            orders_to_renove = saleObj.search([
                ('company_id', '=', company.id),
                ('end_date', '>=', start_date),
                ('end_date', '<=', end_date),
                ('order_renove', '=', False)
            ])

            if orders_to_renove:
                advice_users = self.env['jh.sales.subscription.advice'].search([
                    ('jh_active', '=', True),
                    ('jh_company_id', '=', company.id),
                    ('jh_notify_type', '=', 'email'),
                    ('name.email', '!=', False)
                ])

                if advice_users:
                    body = "<p>Estimado usuario,</p>"
                    body += "<p>Las siguientes suscripciones están próximas a vencer:</p><ul>"

                    for order in orders_to_renove:
                        cliente = order.partner_id.name or "Sin cliente"
                        fecha = order.end_date.strftime('%Y-%m-%d') if order.end_date else "Sin fecha"
                        enlace = order.get_portal_url() if hasattr(order, 'get_portal_url') else '#'
                        body += f"<li>{order.name} – Cliente: {cliente} – Vence el {fecha} – <a href='{enlace}'>Ver orden</a></li>"
                        _logger.info(
                            f"[RENOVACIÓN] Orden incluida: {order.name} – Cliente: {cliente} – Vence el {fecha}")

                    body += "</ul>"
                    body += "<p>Por favor revise estas órdenes para gestionar su renovación.</p>"

                    for advice in advice_users:
                        email_destino = advice.name.email
                        _logger.info(f"[RENOVACIÓN] Se enviaría correo a: {email_destino}")
                        self.env['mail.mail'].create({
                            'subject': 'Suscripciones próximas a vencer',
                            'body_html': body,
                            'email_to': email_destino,
                        }).send()
