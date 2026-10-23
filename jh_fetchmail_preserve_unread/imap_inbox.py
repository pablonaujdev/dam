"""IMAP operations with no dependency on Odoo and no changes to message flags."""


class ImapInbox:
    folder = 'INBOX'

    def __init__(self, connection):
        self.connection = connection

    def select(self):
        # EXAMINE rather than SELECT: the server rejects accidental flag writes.
        status, unused = self.connection.select(self.folder, readonly=True)
        self._check(status)
        return self._number('UIDVALIDITY'), self._number('UIDNEXT')

    def _number(self, name):
        unused, values = self.connection.response(name)
        if not values or not values[0]:
            raise ValueError('IMAP did not return %s; collection stopped.' % name)
        value = int(values[0])
        if value <= 0:
            raise ValueError('Invalid IMAP %s; collection stopped.' % name)
        return value

    def newer_uids(self, last_uid, uid_next, limit):
        if last_uid >= uid_next - 1 or limit <= 0:
            return []
        status, values = self.connection.uid(
            'SEARCH', None, 'UID', '%s:%s' % (last_uid + 1, uid_next - 1))
        self._check(status)
        uids = {int(value) for value in (values[0] or b'').split()}
        # Range searches can return surprising boundary results on some servers.
        return sorted(uid for uid in uids if last_uid < uid < uid_next)[:limit]

    def message(self, uid):
        status, values = self.connection.uid('FETCH', str(uid), '(BODY.PEEK[])')
        self._check(status)
        for value in values or []:
            if isinstance(value, tuple) and len(value) > 1 and isinstance(value[1], bytes):
                return value[1]
        # Confirm absence: an incomplete FETCH must not silently discard a message.
        status, values = self.connection.uid('SEARCH', None, 'UID', '%s:%s' % (uid, uid))
        self._check(status)
        if str(uid).encode() in (values[0] or b'').split():
            raise ValueError('IMAP returned no body for an existing UID; collection stopped.')
        # The UID was expunged between SEARCH and FETCH.
        return None

    @staticmethod
    def _check(status):
        if status != 'OK':
            raise ValueError('IMAP operation failed (%s); collection stopped.' % status)
