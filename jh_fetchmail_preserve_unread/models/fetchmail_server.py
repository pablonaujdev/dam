import hashlib
import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from ..imap_inbox import ImapInbox

_logger = logging.getLogger(__name__)
_LOCK_NAMESPACE = 18902919
_BATCH_LIMIT = 50
_MAX_ATTEMPTS = 3


class FetchmailServer(models.Model):
    _inherit = 'fetchmail.server'

    jh_preserve_unread = fields.Boolean(string='Preserve mailbox read status', default=False, help='Collects new IMAP messages without changing their read status.\nRequires an explicit starting point and does not import earlier messages.')
    jh_uidvalidity = fields.Char(string='IMAP folder generation', readonly=True, copy=False, help='Stores the INBOX generation accepted at the starting point.\nCollection stops if the IMAP server reports a different UIDVALIDITY.')
    jh_last_uid = fields.Char(string='Last scanned UID', readonly=True, copy=False, help='Stores the last message UID recorded by this collector.\nFailed messages are retried separately without scanning processed UIDs again.')
    jh_mailbox_signature = fields.Char(string='Mailbox identity', readonly=True, copy=False, help='Identifies the connection settings accepted at the starting point.\nChanging the server or account requires reconciliation before collecting.')
    jh_collection_error = fields.Text(string='Collection error', readonly=True, copy=False, help='Explains why collection stopped or why a starting point is required.\nMessage processing errors are available in the collection receipts.')
    jh_failed_count = fields.Integer(string='Failed messages', compute='_jh_compute_failed_count', help='Counts messages that still require a successful import.\nOpen the collection receipts to review errors and retry exhausted messages.')

    _sql_constraints = [
        ('jh_fetchmail_mailbox_unique', 'unique(jh_mailbox_signature)',
         'This mailbox already has an initialized collector. Reuse its existing server and receipts.'),
    ]

    def _jh_compute_failed_count(self):
        for server in self:
            server.jh_failed_count = self.env['jh.fetchmail.receipt'].sudo().search_count([
                ('jh_server_id', '=', server.id), ('jh_state', '=', 'failed')])

    @api.constrains('jh_preserve_unread', 'server_type')
    def _jh_check_imap(self):
        for server in self:
            if server.jh_preserve_unread and server._get_connection_type() != 'imap':
                raise ValidationError(_('Preserving read status requires an IMAP server.'))

    def write(self, values):
        protected = {'server', 'port', 'user', 'server_type', 'is_ssl', 'jh_preserve_unread'}
        if protected.intersection(values):
            for server in self:
                if server.jh_uidvalidity and any(
                        server[name] != values[name] for name in protected.intersection(values)):
                    raise UserError(_(
                        'This collector already has a starting point. Archive the server '
                        'to stop it; reconcile its receipts before changing the mailbox or mode.'))
        return super().write(values)

    def _jh_signature(self):
        self.ensure_one()
        identity = '%s|%s|%s|%s|INBOX' % (
            (self.server or '').strip().lower(), self.port,
            (self.user or '').strip().lower(), self.is_ssl)
        return hashlib.sha256(identity.encode()).hexdigest()

    def _jh_open_connection(self):
        return self.connect()

    def _jh_commit(self, processed=False):
        self.env.cr.commit()
        return True

    def _jh_progress_start(self, limit):
        return True

    def _jh_progress_end(self):
        return True

    def _jh_lock(self):
        self.env.cr.execute('SELECT pg_try_advisory_lock(%s, %s)', (_LOCK_NAMESPACE, self.id))
        return self.env.cr.fetchone()[0]

    def _jh_unlock(self):
        self.env.cr.execute('SELECT pg_advisory_unlock(%s, %s)', (_LOCK_NAMESPACE, self.id))

    def _jh_disconnect(self, connection):
        # LOGOUT ends a read-only EXAMINE session without CLOSE/EXPUNGE.
        try:
            connection.logout()
        except Exception:
            _logger.warning('Could not finish read-only IMAP connection for server %s.', self.id)

    def action_jh_initialize(self):
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            raise UserError(_('Only settings administrators can set the starting point.'))
        if not self.active or self.state != 'done' or not self.jh_preserve_unread:
            raise UserError(_('Confirm an active IMAP server and enable preservation first.'))
        if self.jh_uidvalidity:
            raise UserError(_('This server already has a starting point.'))
        if not self._jh_lock():
            raise UserError(_('Collection is running. Try again after it finishes.'))
        connection = None
        try:
            # Another initialization might have committed while this record was cached.
            self.invalidate_recordset()
            if self.jh_uidvalidity:
                raise UserError(_('This server already has a starting point.'))
            connection = self._jh_open_connection()
            generation, uid_next = ImapInbox(connection).select()
            self.sudo().write({
                'jh_uidvalidity': str(generation), 'jh_last_uid': str(uid_next - 1),
                'jh_mailbox_signature': self._jh_signature(), 'jh_collection_error': False,
            })
            # Publish the starting point before releasing the session-level lock.
            self._jh_commit()
        except Exception:
            self.env.cr.rollback()
            raise
        finally:
            if connection:
                self._jh_disconnect(connection)
            self._jh_unlock()
        return True

    def _jh_process_uid(self, inbox, uid, generation, receipt=None):
        Receipt = self.env['jh.fetchmail.receipt'].sudo()
        if receipt is None:
            receipt = Receipt.search([
                ('jh_server_id', '=', self.id), ('jh_folder', '=', inbox.folder),
                ('jh_uidvalidity', '=', str(generation)), ('jh_uid', '=', str(uid))], limit=1)
        if receipt and receipt.jh_state in ('done', 'missing'):
            return
        if not receipt:
            receipt = Receipt.create({
                'jh_server_id': self.id, 'jh_folder': inbox.folder,
                'jh_uidvalidity': str(generation), 'jh_uid': str(uid),
            })
        raw_message = inbox.message(uid)
        if raw_message is None:
            receipt.write({'jh_state': 'missing', 'jh_error': False, 'jh_next_attempt': False})
            return
        attempts = receipt.jh_attempts + 1
        try:
            # Roll back both the business records and success receipt on any failure.
            with self.env.cr.savepoint():
                self.env['mail.thread'].with_context(
                    fetchmail_cron_running=True, default_fetchmail_server_id=self.id,
                    mail_notify_force_send=False,
                ).message_process(
                    self.object_id.model, raw_message, save_original=self.original,
                    strip_attachments=not self.attach)
                receipt.write({'jh_state': 'done', 'jh_attempts': attempts,
                               'jh_error': False, 'jh_next_attempt': False})
        except Exception as error:
            receipt.write({
                'jh_state': 'failed', 'jh_attempts': attempts,
                'jh_next_attempt': fields.Datetime.now() + timedelta(minutes=15),
                'jh_error': '%s: %s' % (type(error).__name__, str(error)[:1000]),
            })
            _logger.warning('IMAP processing failed on server %s, UID %s, attempt %s (%s).',
                            self.id, uid, attempts, type(error).__name__)

    def _jh_collect(self, batch_limit=_BATCH_LIMIT):
        self.ensure_one()
        if not self._jh_lock():
            return None
        connection = None
        result_error = None
        try:
            self.invalidate_recordset()
            if not self.active or self.state != 'done' or not self.jh_preserve_unread:
                return None
            if not self.jh_uidvalidity:
                raise UserError(_('Set the starting point before collecting messages.'))
            if self.jh_mailbox_signature != self._jh_signature():
                raise UserError(_('Mailbox identity changed; reconcile before collecting again.'))
            if not self._jh_progress_start(batch_limit):
                return None
            connection = self._jh_open_connection()
            inbox = ImapInbox(connection)
            generation, uid_next = inbox.select()
            self._jh_validate_inbox(generation, uid_next)
            Receipt = self.env['jh.fetchmail.receipt'].sudo()
            retries = Receipt.search([
                ('jh_server_id', '=', self.id), ('jh_uidvalidity', '=', str(generation)),
                ('jh_folder', '=', inbox.folder), ('jh_state', 'in', ['pending', 'failed']),
                ('jh_attempts', '<', _MAX_ATTEMPTS),
                '|', ('jh_next_attempt', '=', False),
                ('jh_next_attempt', '<=', fields.Datetime.now()),
            ], order='id', limit=max(1, batch_limit // 2))
            count = 0
            for receipt in retries:
                self._jh_process_uid(inbox, int(receipt.jh_uid), generation, receipt=receipt)
                count += 1
                if not self._jh_commit(processed=True):
                    return None
            for uid in inbox.newer_uids(int(self.jh_last_uid or '0'), uid_next, batch_limit - count):
                self._jh_process_uid(inbox, uid, generation)
                # A failed UID is now tracked separately and cannot block newer messages.
                self.sudo().write({'jh_last_uid': str(uid)})
                if not self._jh_commit(processed=True):
                    return None
            self.sudo().write({'date': fields.Datetime.now(), 'jh_collection_error': False})
            self._jh_commit()
        except Exception as error:
            self.env.cr.rollback()
            result_error = error
            self.sudo().write({'jh_collection_error': '%s: %s' % (type(error).__name__, str(error)[:1000])})
            self._jh_commit()
            _logger.warning('Read-only IMAP collection stopped on server %s (%s).',
                            self.id, type(error).__name__)
        finally:
            if connection:
                self._jh_disconnect(connection)
            self._jh_unlock()
            self._jh_progress_end()
        return result_error

    def _jh_validate_inbox(self, generation, uid_next):
        if str(generation) != self.jh_uidvalidity:
            raise UserError(_('IMAP UIDVALIDITY changed; reconcile before collecting again.'))
        if uid_next <= int(self.jh_last_uid or '0'):
            raise UserError(_('IMAP UIDNEXT moved backwards; reconcile before collecting again.'))

    def fetch_mail(self):
        preserving = self.filtered('jh_preserve_unread')
        standard = self - preserving
        result = super(FetchmailServer, standard).fetch_mail() if standard else True
        for server in preserving:
            server.check_access_rights('write')
            server.check_access_rule('write')
            server.sudo().with_context(fetchmail_cron_running=True)._jh_collect()
        return result
