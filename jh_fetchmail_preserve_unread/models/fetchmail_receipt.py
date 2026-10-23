from odoo import fields, models, _
from odoo.exceptions import UserError


class JhFetchmailReceipt(models.Model):
    _name = 'jh.fetchmail.receipt'
    _description = 'IMAP collection receipt'
    _rec_name = 'jh_uid'
    _order = 'id desc'

    jh_server_id = fields.Many2one('fetchmail.server', string='Incoming server', required=True, index=True, ondelete='restrict', help='Identifies the incoming server that collected this message.\nKeep this server and its receipts when migrating the database.')
    jh_folder = fields.Char(string='Folder', required=True, default='INBOX', help='Identifies the IMAP folder associated with the message UID.\nThis implementation collects only INBOX.')
    jh_uidvalidity = fields.Char(string='UIDVALIDITY', required=True, help='Identifies the generation of the IMAP folder.\nA changed value requires reconciliation before collecting again.')
    jh_uid = fields.Char(string='IMAP UID', required=True, help='Identifies this message within its IMAP folder generation.\nStored as text to support unsigned 32-bit IMAP identifiers.')
    jh_state = fields.Selection([('pending', 'Pending'), ('done', 'Processed'), ('failed', 'Failed'), ('missing', 'Removed from mailbox')], string='Result', required=True, default='pending', index=True, help='Records whether this UID was imported or needs another attempt.\nOptions: pending (Pending), done (Processed), failed (Failed), missing (Removed from mailbox).')
    jh_attempts = fields.Integer(string='Attempts', default=0, help='Counts collection attempts since creation or the last manual retry.\nAutomatic collection stops after three unsuccessful attempts.')
    jh_next_attempt = fields.Datetime(string='Next attempt', index=True, help='Indicates when an unsuccessful message can be retried.\nAutomatic retries wait fifteen minutes between attempts.')
    jh_error = fields.Text(string='Last error', help='Explains the latest processing failure for administrator review.\nThe message body and attachments are not stored in this receipt.')

    _jh_fetchmail_uid_unique = models.Constraint(
        'unique(jh_server_id, jh_folder, jh_uidvalidity, jh_uid)',
        'This IMAP message already has a collection receipt.')

    def action_jh_retry(self):
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_('Only settings administrators can retry collection.'))
        # Transaction locks conflict with the collector's session locks and survive
        # until this UI request commits. Never reset a receipt being processed.
        for server in self.mapped('jh_server_id').sorted('id'):
            self.env.cr.execute('SELECT pg_try_advisory_xact_lock(%s, %s)', (18902919, server.id))
            if not self.env.cr.fetchone()[0]:
                raise UserError(_('Collection is running. Try again after it finishes.'))
        self.invalidate_recordset()
        if any(receipt.jh_state != 'failed' for receipt in self):
            raise UserError(_('Only failed messages can be retried.'))
        self.sudo().write({'jh_state': 'pending', 'jh_attempts': 0,
                           'jh_next_attempt': False, 'jh_error': False})
        return True
