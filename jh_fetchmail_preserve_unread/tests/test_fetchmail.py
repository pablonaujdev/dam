from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from ..imap_inbox import ImapInbox
from .fake_imap import FakeImap


@tagged('post_install', '-at_install')
class TestFetchmailPreserveUnread(TransactionCase):
    def setUp(self):
        super().setUp()
        self.server = self.env['fetchmail.server'].create({
            'name': 'Isolated IMAP test', 'server': 'mail.example.invalid',
            'user': 'shared@example.invalid', 'password': 'unused',
            'server_type': 'imap', 'port': 993, 'is_ssl': True,
            'state': 'done', 'jh_preserve_unread': True,
        })
        self.connection = FakeImap({1: b'historical message'})
        self.receipts = self.env['jh.fetchmail.receipt'].sudo()
        # Actual commits would escape TransactionCase's rollback boundary.
        self.commit_patch = patch.object(type(self.server), '_jh_commit', return_value=True)
        self.connect_patch = patch.object(type(self.server), '_jh_open_connection', return_value=self.connection)
        self.progress_start_patch = patch.object(type(self.server), '_jh_progress_start', return_value=True)
        self.progress_end_patch = patch.object(type(self.server), '_jh_progress_end', return_value=True)
        for item in (self.commit_patch, self.connect_patch, self.progress_start_patch, self.progress_end_patch):
            item.start()
            self.addCleanup(item.stop)
        self.server.action_jh_initialize()

    def _receipts(self):
        return self.receipts.search([('jh_server_id', '=', self.server.id)])

    def test_baseline_excludes_history_and_second_poll_does_not_repeat(self):
        self.connection.add(2, b'new message')
        with patch.object(type(self.env['mail.thread']), 'message_process', return_value=123) as process:
            self.assertIsNone(self.server._jh_collect())
            self.assertIsNone(self.server._jh_collect())
        self.assertEqual(process.call_count, 1)
        self.assertEqual(self._receipts().jh_state, 'done')
        self.assertEqual(self.server.jh_last_uid, '2')
        self.assertFalse(self.connection.seen)
        self.assertEqual(process.call_args.args[1], b'new message')

    def test_error_rolls_back_business_record_and_success_receipt(self):
        self.connection.add(2, b'failed message')
        created_name = 'JH import must roll back'

        def fail_after_create(*args, **kwargs):
            self.env['res.partner'].create({'name': created_name})
            raise ValueError('Controlled routing error')

        with patch.object(type(self.env['mail.thread']), 'message_process', side_effect=fail_after_create):
            self.server._jh_collect()
        self.assertFalse(self.env['res.partner'].search([('name', '=', created_name)]))
        receipt = self._receipts()
        self.assertEqual(receipt.jh_state, 'failed')
        self.assertEqual(receipt.jh_attempts, 1)
        self.assertEqual(self.server.jh_last_uid, '2')
        self.assertFalse(self.connection.seen)

    def test_three_failures_stop_automatic_retry_then_manual_retry(self):
        self.connection.add(2, b'failed message')
        with patch.object(type(self.env['mail.thread']), 'message_process', side_effect=ValueError('Controlled error')) as process:
            self.server._jh_collect()
            for unused in range(3):
                self._receipts().write({'jh_next_attempt': fields.Datetime.now() - timedelta(minutes=1)})
                self.server._jh_collect()
        receipt = self._receipts()
        self.assertEqual(process.call_count, 3)
        self.assertEqual(receipt.jh_attempts, 3)
        receipt.action_jh_retry()
        with patch.object(type(self.env['mail.thread']), 'message_process', return_value=123) as process:
            self.server._jh_collect()
            self.server._jh_collect()
        self.assertEqual(process.call_count, 1)
        self.assertEqual(receipt.jh_state, 'done')

    def test_read_message_is_collected_without_changing_flags(self):
        self.connection.add(2, b'read message')
        self.connection.seen.add(2)
        with patch.object(type(self.env['mail.thread']), 'message_process', return_value=123):
            self.server._jh_collect()
        self.assertEqual(self._receipts().jh_state, 'done')
        self.assertEqual(self.connection.seen, {2})

    def test_completed_receipt_cannot_be_retried(self):
        self.connection.add(2, b'new message')
        with patch.object(type(self.env['mail.thread']), 'message_process', return_value=123):
            self.server._jh_process_uid(ImapInbox(self.connection), 2, 42)
        with self.assertRaises(UserError):
            self._receipts().action_jh_retry()

    def test_mode_and_mailbox_cannot_change_after_initialization(self):
        for values in ({'jh_preserve_unread': False}, {'user': 'other@example.invalid'}, {'server': 'other.example.invalid'}):
            with self.assertRaises(UserError):
                self.server.write(values)

    def test_expunged_message_is_terminal_without_business_import(self):
        with patch.object(type(self.env['mail.thread']), 'message_process') as process:
            self.server._jh_process_uid(ImapInbox(self.connection), 2, 42)
        self.assertFalse(process.called)
        self.assertEqual(self._receipts().jh_state, 'missing')

    def test_uidvalidity_change_stops_without_resetting_cursor(self):
        with self.assertRaises(UserError):
            self.server._jh_validate_inbox(99, 2)
        self.assertEqual(self.server.jh_uidvalidity, '42')
        self.assertEqual(self.server.jh_last_uid, '1')

    def test_backwards_uidnext_stops(self):
        with self.assertRaises(UserError):
            self.server._jh_validate_inbox(42, 1)

    def test_second_worker_cannot_acquire_mailbox_lock(self):
        self.assertTrue(self.server._jh_lock())
        try:
            with self.registry.cursor() as other_cr:
                other_cr.execute('SELECT pg_try_advisory_lock(%s, %s)', (18902919, self.server.id))
                acquired = other_cr.fetchone()[0]
                if acquired:
                    other_cr.execute('SELECT pg_advisory_unlock(%s, %s)', (18902919, self.server.id))
                self.assertFalse(acquired)
        finally:
            self.server._jh_unlock()
