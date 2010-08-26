"""Changeset reconstruction logic for CVSGit."""

import time

QUIET_PERIOD = 60

FILE_ADDED = 'A'
FILE_DELETED = 'D'
FILE_MODIFIED = 'M'

class Change(object):

    def __init__(self, timestamp, author, log, filename, revision, state):
        self.timestamp = timestamp
        self.author = author
        self.log = log
        self.filename = filename
        self.revision = revision
        self.state = state

class ChangeSet(object):

    def __init__(self, change, id=None, mark=None, provider=None):
        """'id' is an arbitrary value to distinguish this changeset.

        'mark' is a commit marker that, if not None, identifies this
        changeset as having been integrated.

        The 'provider' argument, if set, should be an object that has
        a blob() method accepting a Change object as an argument and
        returning the binary data for the file as it was after the
        change."""

        self.id = id
        self.mark = mark
        self.provider = provider
        self.start_time = change.timestamp
        self.end_time = change.timestamp
        self.changes = [change]

    def blob(self, change):
        if self.provider is None:
            raise RuntimeError, \
                'no provider has been set for this changeset'
        return self.provider.blob(change)

    def get_timestamp(self):
        return self.start_time

    def get_author(self):
        return self.changes[0].author

    def get_log(self):
        return self.changes[0].log

    def get_filenames(self):
        return map(lambda c: c.filename, self.changes)

    timestamp = property(get_timestamp)
    author = property(get_author)
    log = property(get_log)
    filenames = property(get_filenames)

    def integrate(self, change):
        if change.author != self.author or \
           change.log != self.log or \
           change.filename in self.filenames:
            return False

        if change.timestamp < self.start_time:
            self.start_time = change.timestamp
        elif change.timestamp > self.end_time:
            self.end_time = change.timestamp

        self.changes.append(change)
        return True

class ChangeSetGenerator(object):
    """Group a series of individual file changes into changesets that
    have likely been committed together.  The individual changes must
    be presented in ascending order of their timestamp."""

    def __init__(self, quiet_period=QUIET_PERIOD):
        self.quiet_period = quiet_period
        self.changesets = []

    def integrate(self, change):
        """Integrate a single file change into the an appropriate
        changeset and yield changesets that haven't been modified for
        at least the "quiet period", relative to the given change."""

        # Yield changesets that have passed the "quiet period".
        changesets = []
        for cs in self.changesets:
            delta = change.timestamp - cs.end_time
            if delta >= self.quiet_period:
                yield(cs)
            else:
                changesets.append(cs)
        self.changesets = changesets

        # For all remaining changesets, try to find one that can
        # integrate the change.  Otherwise, open a new changeset.
        for cs in self.changesets:
            if cs.integrate(change):
                return
        self.changesets.append(ChangeSet(change))

    def finalize(self):
        """Yield remaining changesets that have passed the "quiet
        period", relative to the current system time.  Changesets that
        are still within the quiet period will be kept back until
        further changes are integrated with integrate() or until
        finalize() is called again when some time has passed."""

        #FIXME: time zones aren't handled correctly - need unit tests!
        now = int(time.time())
        changesets = []
        for cs in self.changesets:
            delta = now - cs.end_time
            if delta >= self.quiet_period:
                yield(cs)
            else:
                changesets.append(cs)
        self.changesets = changesets
