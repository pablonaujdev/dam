import hashlib
from email.message import EmailMessage
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged

from .fake_imap import FakeImap


@tagged('post_install', '-at_install')
class TestPersonalReplies(TransactionCase):
    def setUp(self):
        super().setUp()
        self.alias_domain = self.env['mail.alias.domain'].create({
            'name': 'reply-lab.invalid', 'catchall_alias': 'office', 'bounce_alias': 'bounce',
        })
        self.env.company.alias_domain_id = self.alias_domain
        self.user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Personal reply pilot', 'login': 'pilot@local.test',
            'email': 'pilot@local.test', 'notification_type': 'email',
        })
        self.server = self.env['fetchmail.server'].create({
            'name': 'Personal replies test', 'server': 'mail.example.invalid',
            'user': self.user.email, 'password': 'unused', 'server_type': 'imap',
            'port': 993, 'is_ssl': True, 'state': 'done',
            'jh_preserve_unread': True, 'jh_replies_only': True,
            'jh_reply_user_id': self.user.id,
        })
        self.connection = FakeImap()
        for name, kwargs in [
            ('_jh_commit', {'return_value': True}),
            ('_jh_open_connection', {'return_value': self.connection}),
            ('_jh_progress_start', {'return_value': True}),
            ('_jh_progress_end', {'return_value': True}),
        ]:
            mock = patch.object(type(self.server), name, **kwargs)
            mock.start()
            self.addCleanup(mock.stop)
        self.server.action_jh_initialize()
        self.server.jh_reply_to_sender = True
        self.document = self.env['res.partner'].with_context(mail_create_nosubscribe=True).create({
            'name': 'Reply test document',
        })
        self.document.message_subscribe(partner_ids=[self.user.partner_id.id])
        self.original = self.document.with_context(mail_notify_force_send=False).message_post(
            body='Outbound test', message_type='comment', subtype_xmlid='mail.mt_comment',
            email_from='Pilot <pilot@local.test>', author_id=self.user.partner_id.id,
        )

    def _raw(self, message_id='<reply-1@local.test>', references=True):
        message = EmailMessage()
        message['From'] = 'Customer <customer@local.test>'
        message['To'] = 'Pilot <pilot@local.test>'
        message['Subject'] = 'Re: Odoo test'
        if message_id:
            message['Message-ID'] = message_id
        if references:
            message['In-Reply-To'] = self.original.message_id
            message['References'] = self.original.message_id
        message.set_content('Customer reply')
        message.add_attachment(b'test attachment', maintype='application', subtype='octet-stream', filename='test.txt')
        return message.as_bytes()

    def _collect(self, uid=1, raw=None, server=None):
        self.connection.add(uid, raw if raw is not None else self._raw())
        self.assertIsNone((server or self.server)._jh_collect())
        return self.env['jh.fetchmail.receipt'].search([
            ('jh_server_id', '=', (server or self.server).id), ('jh_uid', '=', str(uid)),
        ])

    def test_outgoing_reply_to_uses_sender_and_unconfigured_sender_keeps_native(self):
        self.assertEqual(self.original.reply_to, 'Pilot <pilot@local.test>')
        result = self.document._notify_get_reply_to(default='Other <other@local.test>')
        self.server.jh_reply_to_sender = False
        self.assertEqual(self.document._notify_get_reply_to(default='Other <other@local.test>'), result)
        native = self.document._notify_get_reply_to(default='Pilot <pilot@local.test>')
        self.server.jh_reply_to_sender = True
        self.assertEqual(self.document.with_context(fetchmail_cron_running=True)._notify_get_reply_to(
            default='Pilot <pilot@local.test>'), native)

    def test_explicit_reply_to_is_preserved(self):
        message = self.document.with_context(mail_notify_force_send=False).message_post(
            body='Explicit destination', email_from='Pilot <pilot@local.test>',
            reply_to='special@local.test', message_type='comment',
        )
        self.assertEqual(message.reply_to, 'special@local.test')

    def test_valid_reply_imported_once_with_attachment_and_no_duplicate_notification(self):
        receipt = self._collect()
        self.assertEqual(receipt.jh_state, 'done')
        self.server._jh_collect()
        messages = self.env['mail.message'].search([('message_id', '=', '<reply-1@local.test>')])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages.model, self.document._name)
        self.assertEqual(messages.res_id, self.document.id)
        self.assertIn('test.txt', messages.attachment_ids.mapped('name'))
        self.assertFalse(self.connection.seen)
        self.assertFalse(self.env['mail.notification'].search([
            ('mail_message_id', '=', messages.id), ('res_partner_id', '=', self.user.partner_id.id),
            ('notification_type', '=', 'email'),
        ]))

    def test_unrelated_mail_skipped_without_business_records_or_bounces(self):
        message_count = self.env['mail.message'].search_count([])
        mail_count = self.env['mail.mail'].search_count([])
        receipt = self._collect(raw=self._raw(references=False))
        self.assertEqual(receipt.jh_state, 'skipped')
        self.assertFalse(receipt.jh_message_key)
        self.assertEqual(self.env['mail.message'].search_count([]), message_count)
        self.assertEqual(self.env['mail.mail'].search_count([]), mail_count)
        self.server._jh_collect()
        self.assertEqual(receipt.jh_attempts, 1)

    def test_copy_received_in_second_mailbox_is_duplicate(self):
        second = self.server.copy({'user': 'second@local.test', 'jh_reply_user_id': False, 'state': 'done'})
        second.action_jh_initialize()
        self._collect()
        receipt = self._collect(server=second)
        self.assertEqual(receipt.jh_state, 'duplicate')
        self.assertFalse(receipt.jh_message_key)
        self.assertEqual(self.env['mail.message'].search_count([('message_id', '=', '<reply-1@local.test>')]), 1)

    def test_unique_claim_survives_deleted_business_message(self):
        self._collect()
        self.env['mail.message'].search([('message_id', '=', '<reply-1@local.test>')]).unlink()
        with self.cr.savepoint():
            receipt = self._collect(uid=2)
        self.assertEqual(receipt.jh_state, 'duplicate')
        self.assertFalse(self.env['mail.message'].search([('message_id', '=', '<reply-1@local.test>')]))

    def test_failed_import_rolls_back_claim_then_retry_succeeds(self):
        with patch.object(type(self.env['mail.thread']), 'message_process', side_effect=ValueError('Controlled failure')):
            receipt = self._collect()
        self.assertEqual(receipt.jh_state, 'failed')
        self.assertFalse(receipt.jh_message_key)
        receipt.action_jh_retry()
        self.server._jh_collect()
        self.assertEqual(receipt.jh_state, 'done')
        self.assertEqual(receipt.jh_message_key, hashlib.sha256(b'<reply-1@local.test>').hexdigest())

    def test_related_reply_without_message_id_is_failed_not_silently_imported(self):
        receipt = self._collect(raw=self._raw(message_id=None))
        self.assertEqual(receipt.jh_state, 'failed')
        self.assertIn('Message-ID', receipt.jh_error)

    def test_initialization_required_and_mailbox_owner_must_match(self):
        self.server.jh_reply_to_sender = False
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.server.write({'jh_uidvalidity': False, 'jh_reply_to_sender': True})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.server.write({'jh_reply_user_id': self.env.user.id, 'jh_reply_to_sender': True})

    def test_changed_user_email_automatically_disables_personal_reply_routing(self):
        self.user.email = 'different@local.test'
        self.assertNotIn('pilot@local.test', self.server._jh_reply_addresses())

    def test_deleted_document_reply_is_failed_not_sent_to_fallback(self):
        raw = self._raw()
        self.document.unlink()
        receipt = self._collect(raw=raw)
        # Odoo may remove the original message with its document. In that case
        # it is unrelated; otherwise the stale reference is a visible failure.
        self.assertIn(receipt.jh_state, ('failed', 'skipped'))
        self.assertFalse(self.env['mail.message'].search([('message_id', '=', '<reply-1@local.test>')]))

    def test_loop_or_silent_rejection_is_not_marked_processed(self):
        with patch.object(type(self.env['mail.thread']), 'message_process', return_value=False):
            receipt = self._collect()
        self.assertEqual(receipt.jh_state, 'failed')
        self.assertFalse(receipt.jh_message_key)

    def test_other_email_followers_still_receive_notification(self):
        follower = self.env['res.partner'].create({'name': 'Other follower', 'email': 'follower@local.test'})
        self.document.message_subscribe(partner_ids=follower.ids)
        self._collect()
        message = self.env['mail.message'].search([('message_id', '=', '<reply-1@local.test>')])
        self.assertTrue(self.env['mail.notification'].search([
            ('mail_message_id', '=', message.id), ('res_partner_id', '=', follower.id),
            ('notification_type', '=', 'email'),
        ]))

    def test_office_copy_collected_first_does_not_notify_personal_recipient_twice(self):
        office = self.server.copy({
            'user': 'office@local.test', 'jh_reply_user_id': False,
            'jh_replies_only': False, 'state': 'done',
        })
        office.action_jh_initialize()
        self.assertEqual(self._collect(server=office).jh_state, 'done')
        self.assertEqual(self._collect().jh_state, 'duplicate')
        message = self.env['mail.message'].search([('message_id', '=', '<reply-1@local.test>')])
        self.assertFalse(self.env['mail.notification'].search([
            ('mail_message_id', '=', message.id), ('res_partner_id', '=', self.user.partner_id.id),
            ('notification_type', '=', 'email'),
        ]))

    def test_reply_to_alias_for_other_model_does_not_create_new_document(self):
        alias = self.env['mail.alias'].create({
            'alias_name': 'other-route', 'alias_domain_id': self.alias_domain.id,
            'alias_model_id': self.env['ir.model']._get_id('fetchmail.server'),
        })
        # The alternate alias must not override a personal-mailbox reply reference.
        message = EmailMessage()
        message['From'] = 'customer@local.test'
        message['To'] = alias.alias_full_name
        message['Message-ID'] = '<wrong-route@local.test>'
        message['References'] = self.original.message_id
        message.set_content('Must not create a record through another alias')
        count = self.env['fetchmail.server'].search_count([])
        receipt = self._collect(raw=message.as_bytes())
        self.assertEqual(receipt.jh_state, 'failed')
        self.assertEqual(self.env['fetchmail.server'].search_count([]), count)
        self.assertFalse(self.env['mail.message'].search([('message_id', '=', '<wrong-route@local.test>')]))
