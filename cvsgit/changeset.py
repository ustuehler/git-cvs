"""Changeset reconstruction logic for CVSGit."""

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

    def __str__(self):
        return '<%s %s, %s, %s %s %s %s>' % \
            (type(self).__name__, self.timestamp, self.author,
             self.filestatus, self.filename, self.revision, self.state)

class ChangeSet(object):
    """A set of Change objects that represent a CVS commit.

    The ChangeSet class represents a set of related RCS changes
    that appear to have been made in the same CVS commit.  The
    ChangeSetGenerator class constructs instances of ChangeSet.

    One or more Change objects can be integrated into a ChangeSet
    like so:

    >>> c1 = Change(1303768245, "jack", "Initial commit", FILE_ADDED,
    ... "todo.txt", "1.1", "state???", "mode???")
    >>> c2 = Change(1303768249, "jack", "Initial commit", FILE_ADDED,
    ... "README", "1.1", "state???", "mode???")
    >>> cs = ChangeSet(c1)
    >>> cs.integrate(c2)
    True
    >>> cs.log
    'Initial commit'
    >>> cs.start_time < cs.end_time
    True

    The following is a little odd, but currently wanted behaviour in
    order to make it easier to emulate a peculiarity of cvs.  The
    timestamp is always one second ahead of end_time:

    >>> cs.timestamp > cs.end_time
    True
    >>> cs.timestamp
    1303768250

    The timestamp returned for the changeset is based on the timestamp
    of the last change in the set because that is most likely the time
    when the commit actually completed and "cvs -D <timestamp>" can be
    used to create an equivalent working copy from CVS.
    """

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

    def perm(self, change):
        return self.provider.perm(change)

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

    def __str__(self):
        if len(self.changes) == 1:
            changes = '1 file'
        else:
            changes = '%d files' % len(self.changes)
        return '<%s %s, %s, %s, %s>' % \
            (type(self).__name__, self.timestamp, self.author, changes,
             self.mark)

class ChangeSetGenerator(object):
    """Group a series of individual file changes into changesets that
    have likely been committed together.  The individual changes must
    be presented in ascending order of their timestamp."""

    def __init__(self, quiet_period=QUIET_PERIOD, limit=None):
        """Construct a new ChangeSetGenerator instance.

        The ChangeSetGenerator should only return complete ChangeSets
        and retain possibly incomplete ChangeSets.  If limit is given,
        only return as many changesets and retain all others.

        Major reasons for incomplete ChangeSets:

        1. When importing Changes directly from a writable CVS
           repository (without locking against CVS clients) we could
           be racing against "cvs commit" and other operations.

        2. When importing from a CVS repository mirror, the mirroring
           may have overlapped with a "cvs commit" or other operation,
           again unless CVS clients were locked out for that time.

        3. If the CVS mirror operation was interrupted, some RCS files
           belonging to a ChangeSet may have been updated while others
           have not.

        To guard against all of the above, the ChangeSetGenerator
        defines a ChangeSet `X' as being complete only if there is
        another ChangeSet `Y' and `Y.start_time - X.end_time >
        quiet_period`, i.e., after the complete ChangeSet there is at
        least one significantly younger one.
        """

        self.quiet_period = quiet_period
        self.limit = limit
        self.count = 0
        self.changesets = []

    def integrate(self, change):
        """Integrate a single file change into the an appropriate
        changeset and yield changesets that haven't been modified for
        at least the "quiet period", relative to the given change."""

        # Yield changesets that have passed the "quiet period".
        changesets = []
        count = self.count
        for cs in self.changesets:
            delta = change.timestamp - cs.end_time
            if delta >= self.quiet_period:
                if self.limit and count >= self.limit:
                    return
                count += 1
                yield(cs)
            else:
                changesets.append(cs)
        self.changesets = changesets
        self.count = count

        # For all remaining changesets, try to find one that can
        # integrate the change.  Otherwise, open a new changeset.
        for cs in self.changesets:
            if cs.integrate(change):
                return
        self.changesets.append(ChangeSet(change))

        # TODO: Is changeset ordering more stable with this?
        #self.changesets.sort(key=lambda cs: cs.timestamp)

    def flush(self):
        """Yield remaining changesets up to the limit (if one was set),
        even potentially incomplete ones."""

        count = self.count
        for cs in self.changesets:
            if self.limit and count >= self.limit:
                return
            count += 1
            yield(cs)
        self.changesets = []
        self.count = count
