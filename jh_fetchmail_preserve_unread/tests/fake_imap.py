class FakeImap:
    """A mailbox where any attempt to mutate flags or delete mail fails the test."""

    def __init__(self, messages=None, generation=42, uid_next=None):
        self.messages = dict(messages or {})
        self.generation = generation
        self.uid_next = uid_next or max(self.messages, default=0) + 1
        self.calls = []
        self.seen = set()
        self.status = 'OK'
        self.search_override = None
        self.fetch_error = None
        self.omit_body = False

    def select(self, folder='INBOX', readonly=False):
        assert folder == 'INBOX' and readonly, 'Mailbox must be opened read-only'
        self.calls.append(('EXAMINE', folder))
        return self.status, [str(len(self.messages)).encode()]

    def response(self, name):
        value = {'UIDVALIDITY': self.generation, 'UIDNEXT': self.uid_next}[name]
        return name, [str(value).encode() if value is not None else None]

    def uid(self, operation, *args):
        self.calls.append((operation, *args))
        if operation == 'SEARCH':
            assert args[0] is None and args[1] == 'UID', 'Do not filter by UNSEEN'
            if self.search_override is not None:
                return self.status, [self.search_override]
            start, end = map(int, args[2].split(':'))
            result = sorted(uid for uid in self.messages if start <= uid <= end)
            return self.status, [' '.join(map(str, result)).encode()]
        if operation == 'FETCH':
            assert args[1] == '(BODY.PEEK[])', 'Fetching must not mark mail read'
            if self.fetch_error:
                raise self.fetch_error
            uid = int(args[0])
            if uid not in self.messages or self.omit_body:
                return self.status, [None]
            return self.status, [(b'1 (UID %d BODY[] {10})' % uid, self.messages[uid]), b')']
        raise AssertionError('Unexpected IMAP operation: %s' % operation)

    def store(self, *args):
        raise AssertionError('Flags must never be changed')

    def close(self):
        raise AssertionError('Do not CLOSE or EXPUNGE a shared mailbox')

    def logout(self):
        self.calls.append(('LOGOUT',))

    def add(self, uid, message):
        self.messages[uid] = message
        self.uid_next = max(self.uid_next, uid + 1)
