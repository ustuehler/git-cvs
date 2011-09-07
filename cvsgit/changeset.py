"""Changeset reconstruction logic for CVSGit."""

import time

QUIET_PERIOD = 60

FILE_ADDED = 'A'
FILE_DELETED = 'D'
FILE_MODIFIED = 'M'

class Change(object):
    """Representation of a single change in an RCS file.

    For example:
    >>> Change(1303768248, "jack", "ToDo list added", FILE_ADDED,
    ... "todo.txt", "1.1", "state???", "mode???").author
    'jack'

    The time stamp should be in UTC time zone. The state and mode
    arguments in the above example are bogus, which illustrates
    that this class is really just a dumb container.

    Change objects are integrated into a ChangeSet by a
    ChangeSetGenerator."""

    def __init__(self, timestamp, author, log, filestatus, filename,
                 revision, state, mode):
        self.timestamp = timestamp
        self.author = author
        self.log = log
        self.filestatus = filestatus
        self.filename = filename
        self.revision = revision
        self.state = state
        self.mode = mode

class ChangeSet(object):
    """A set of Change objects that represent a CVS commit.

    The ChangeSet class represents a set of related RCS changes
    that appear to have been made in the same CVS commit.  The
    ChangeSetGenerator class constructs instances of ChangeSet.

    One or more Change objects can be integrated into a ChangeSet
    like so:
    >>> c1 = Change(1303768248, "jack", "Initial commit", FILE_ADDED,
    ... "todo.txt", "1.1", "state???", "mode???")
    >>> c2 = Change(1303768249, "jack", "Initial commit", FILE_ADDED,
    ... "README", "1.1", "state???", "mode???")
    >>> cs = ChangeSet(c1)
    >>> cs.integrate(c2)
    True
    >>> cs.log
    'Initial commit'
    >>> cs.timestamp
    1303768249
    >>> cs.timestamp == cs.end_time
    True
    >>> cs.start_time < cs.end_time
    True

    Note that the timestamp returned is that of the last change in
    the set, because that is most likely the time when the CVS commit
    was actually completed."""

    def __init__(self, change, id=None, mark=None, provider=None):
        """'id' is an arbitrary value to distinguish this changeset.

        'mark' is a commit marker that, if not None, identifies this
        changeset as having been integrated.

        The 'provider' argument, if set, should be an object that has
        a blob() method accepting a Change object as an argument and
        returning the binary data for the file as it was after the
        change."""

        self.id = id
        self._mark = mark
        self._provider = provider
        self.start_time = change.timestamp
        self.end_time = change.timestamp
        self.changes = [change]

    def get_provider(self):
        if self._provider is None:
            raise RuntimeError, \
                'no provider has been set for this changeset'
        return self._provider

    def set_provider(self, provider):
        self._provider = provider

    provider = property(get_provider, set_provider, None,
                        'source VCS of this changeset')

    def get_mark(self):
        return self._mark

    def set_mark(self, mark):
        self._mark = mark
        self.provider.mark_changeset(self)

    mark = property(get_mark, set_mark, None,
                    """anything but None marks the changeset as
                    integrated into the target VCS""")

    def blob(self, change):
        return self.provider.blob(change, self)

    def get_timestamp(self):
        # At first, this method returned start_time, but it makes more
        # sense to return end_time, which is when the last RCS change
        # happend that affected this changeset.  This should make it
        # more likely that a "cvs checkout -D <timestamp>" yields the
        # expected result when <timestamp> is that of the changeset.

        # FIXME: end_time + 1 is a lie
        # It is however an easy workaround to make the initial
        # revisions be 1.1 instead of 1.1.1.1 (consistently, in both
        # "cvs co -D <date>" and in the cloned Git repository.)
        return self.end_time + 1

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
        """Construct a new ChangeSetGenerator instance.

        We don't want CVS commits spanning multiple files that were
        not finished while we synced the CVS mirror to be accepted
        as complete changesets.  The "quiet period" guards against
        such incomplete change sets by requiring that any CVS change
        must be older than the current system time minus the quiet
        period (in seconds).  (Assuming that the system time and
        CVS time stamps are not totally bogus, of course.)"""

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
