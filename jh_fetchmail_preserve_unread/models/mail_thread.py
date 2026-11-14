from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools.mail import email_normalize, email_split


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_get_reply_to(self, default=None):
        replies = super()._notify_get_reply_to(default=default)
        if not self.env.context.get('fetchmail_cron_running'):
            address = email_normalize(default or '')
            if address and address in self.env['fetchmail.server']._jh_reply_addresses():
                replies = dict.fromkeys(replies, default)
        return replies

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        routes = super().message_route(message, message_dict, model, thread_id, custom_values)
        parent_id = self.env.context.get('jh_reply_parent_id')
        if parent_id:
            parent = self.env['mail.message'].sudo().browse(parent_id).exists()
            if not parent or not routes or any(
                    route[0] != parent.model or route[1] != parent.res_id for route in routes):
                raise UserError(_('The reply could not be routed to its original Odoo document.'))
        return routes

    def _routing_create_bounce_email(self, email_from, body_html, message, **mail_values):
        if self.env.context.get('jh_reply_parent_id'):
            # The native helper sends immediately. Stop before that external side
            # effect so the collector can roll back and record the routing error.
            raise UserError(_('Odoo rejected this reply; review the document alias and sender permissions.'))
        return super()._routing_create_bounce_email(email_from, body_html, message, **mail_values)

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        recipients = super()._notify_get_recipients(message, msg_vals, **kwargs)
        original = self.env.context.get('jh_original_recipients')
        if not original:
            return recipients
        addresses = {email_normalize(address) for address in email_split(original)}
        # Internal users already received the original in Outlook. Keep native
        # inbox notifications and notifications to other followers unchanged.
        partners = self.env['res.partner'].sudo().browse([
            recipient['id'] for recipient in recipients
            if recipient['type'] == 'user' and recipient['notif'] == 'email'
        ])
        delivered = set(partners.filtered(lambda partner: partner.email_normalized in addresses).ids)
        return [recipient for recipient in recipients if recipient['id'] not in delivered]
