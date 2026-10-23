"""Run with Python directly; no Odoo, database or external mailbox is required."""
import importlib.util
from pathlib import Path
import unittest


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
ImapInbox = load_file('jh_imap_inbox', ROOT / 'imap_inbox.py').ImapInbox
FakeImap = load_file('jh_fake_imap', ROOT / 'tests' / 'fake_imap.py').FakeImap


class TestImapInbox(unittest.TestCase):
    def setUp(self):
        self.connection = FakeImap({3: b'three', 7: b'seven', 12: b'twelve'})
        self.inbox = ImapInbox(self.connection)

    def test_select_is_readonly(self):
        self.assertEqual(self.inbox.select(), (42, 13))
        self.assertEqual(self.connection.calls, [('EXAMINE', 'INBOX')])

    def test_new_mail_includes_read_and_unread(self):
        self.connection.seen.add(7)
        self.assertEqual(self.inbox.newer_uids(3, 13, 50), [7, 12])
        self.assertEqual(self.connection.seen, {7})

    def test_repeat_poll_excludes_previous_uid(self):
        uids = self.inbox.newer_uids(3, 13, 50)
        self.assertEqual(self.inbox.newer_uids(uids[-1], 13, 50), [])

    def test_fetch_preserves_unread(self):
        self.assertEqual(self.inbox.message(7), b'seven')
        self.assertFalse(self.connection.seen)

    def test_fetch_preserves_read(self):
        self.connection.seen.add(7)
        self.assertEqual(self.inbox.message(7), b'seven')
        self.assertEqual(self.connection.seen, {7})

    def test_expunged_message(self):
        self.assertIsNone(self.inbox.message(99))

    def test_batch_limit(self):
        self.assertEqual(self.inbox.newer_uids(0, 13, 2), [3, 7])

    def test_no_budget_does_not_search(self):
        self.assertEqual(self.inbox.newer_uids(0, 13, 0), [])
        self.assertFalse(self.connection.calls)

    def test_no_reversed_range_for_empty_mailbox(self):
        self.assertEqual(self.inbox.newer_uids(0, 1, 50), [])
        self.assertFalse(self.connection.calls)

    def test_uidnext_snapshot_excludes_later_arrival(self):
        self.connection.add(15, b'new')
        self.assertEqual(self.inbox.newer_uids(7, 13, 50), [12])

    def test_duplicates_and_out_of_range_results(self):
        self.connection.search_override = b'3 7 7 12 99'
        self.assertEqual(self.inbox.newer_uids(3, 13, 50), [7, 12])

    def test_uid_above_signed_integer_limit(self):
        self.connection.add(4294967294, b'large uid')
        self.assertEqual(self.inbox.newer_uids(4294967293, 4294967295, 50), [4294967294])

    def test_select_failure(self):
        self.connection.status = 'NO'
        with self.assertRaises(ValueError):
            self.inbox.select()

    def test_missing_uidvalidity_stops(self):
        self.connection.generation = None
        with self.assertRaises(ValueError):
            self.inbox.select()

    def test_missing_uidnext_stops(self):
        self.connection.uid_next = None
        with self.assertRaises(ValueError):
            self.inbox.select()

    def test_failed_search_stops(self):
        self.connection.status = 'BAD'
        with self.assertRaises(ValueError):
            self.inbox.newer_uids(0, 13, 50)

    def test_failed_fetch_stops(self):
        self.connection.status = 'NO'
        with self.assertRaises(ValueError):
            self.inbox.message(7)

    def test_socket_error_propagates(self):
        self.connection.fetch_error = OSError('Connection interrupted')
        with self.assertRaises(OSError):
            self.inbox.message(7)

    def test_existing_uid_without_body_is_not_silently_discarded(self):
        self.connection.omit_body = True
        with self.assertRaises(ValueError):
            self.inbox.message(7)


if __name__ == '__main__':
    unittest.main()
