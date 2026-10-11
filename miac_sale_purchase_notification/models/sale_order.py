# Part of Avannubo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import Command, _, models
from odoo.tools import email_normalize

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        self.check_access('read')
        # Native service procurement elevates purchase access on these sale lines.
        # Confine that elevation to links belonging to accessible sales.
        existing_lines = {
            order.id: set(order.order_line.sudo().purchase_line_ids.ids)
            for order in self
        }
        result = super().action_confirm()
        for order in self:
            new_license_lines = order.order_line.sudo().purchase_line_ids.filtered(
                lambda line: line.id not in existing_lines[order.id]
                and line.product_id.recurring_invoice
            )
            if new_license_lines:
                order.with_company(order.company_id)._notify_license_purchase()
        return result

    def _license_purchase_note(self, body):
        self.ensure_one()
        self.with_context(mail_notify_force_send=False).message_post(
            body=body, subtype_xmlid='mail.mt_note', partner_ids=[],
            notify_skip_followers=True,
        )

    def _notify_license_purchase(self):
        self.ensure_one()
        try:
            # Roll back only this mail attempt if rendering or mail creation fails.
            with self.env.cr.savepoint():
                recipient = self.company_id.notify_purchase_license_id
                recipient.check_access('read')
                if not recipient or not email_normalize(recipient.email or ''):
                    self._license_purchase_note(_(
                        'License purchases were created. No notice was queued because '
                        'the company notification recipient is missing or has no single valid email.'
                    ))
                    return
                template = self.env.ref(
                    'miac_sale_purchase_notification.email_template_sale_purchase_license',
                    raise_if_not_found=False,
                )
                if not template:
                    self._license_purchase_note(_(
                        'License purchases were created. No notice was queued '
                        'because the license purchase email template is missing.'
                    ))
                    return
                template.send_mail(self.id, force_send=False, email_values={
                    'recipient_ids': [Command.set([recipient.id])],
                    'email_to': False,
                    'email_cc': False,
                })
        except Exception:
            _logger.exception('Could not queue license purchase notice for sale %s', self.id)
            self._license_purchase_note(_(
                'License purchases were created, but their email notice could not be '
                'generated. The sale and purchases are preserved; please contact an administrator.'
            ))
