"""CVS-to-Git mapping database for CVSGit."""

import re
import sqlite3

FILE_ADDED = 'A'
FILE_DELETED = 'D'
FILE_MODIFIED = 'M'

class Db(object):
    """Fast CVS repository index.  Maintains state of the incremental
    import of a CVS repository into Git."""

    # As of now the database contains only revisions from the CVS
    # repository that are pending to be grouped into changesets.

    def __init__(self, filename):
        self.filename = filename
        self.dbh = sqlite3.connect(filename)

        # Create the main database table.
        sql = 'CREATE TABLE IF NOT EXISTS revision (' \
              'file VARCHAR NOT NULL, ' \
              'revision VARCHAR NOT NULL, ' \
              'author VARCHAR NOT NULL, ' \
              'timestamp DATETIME NOT NULL, ' \
              'log TEXT NOT NULL, ' \
              'state VARCHAR(8) NOT NULL, ' \
              'PRIMARY KEY (file, revision))'

        self.dbh.execute(sql)

    def add_revision(self, revision):
        """Insert an RCS revision into the database.  'revision'
        should be an RCSRevision object.  Multiple inserts may be
        queued for performance.  The caller must call commit() after
        any number of inserts to ensure that the changes get flushed
        to disk."""

        sql = 'INSERT OR IGNORE INTO revision (file, revision, ' \
              'timestamp, author, log, state) VALUES (?,?,?,?,?,?)'

        assert(revision.rcsfile.filename.endswith(',v'))
        file = revision.rcsfile.filename
        file = re.sub('(Attic/)?([^/]+),v$', '\\2', file)
        values = (file,
                  revision.revision,
                  revision.timestamp,
                  revision.author,
                  revision.log,
                  revision.state,)

        self.dbh.execute(sql, values)

    def commit(self):
        self.dbh.commit()

    def changesets(self):
        "Yield changesets reconstructed from RCS revisions."
        csg = ChangeSetGenerator()
        sql = 'SELECT timestamp, author, log, file, revision, state ' \
              'FROM revision ORDER BY timestamp'
        for row in self.dbh.execute(sql).fetchall():
            change = Change(*row)
            for cs in csg.integrate(change):
                yield(cs)
        for cs in csg.finalize():
            yield(cs)

class Change(object):
    def __init__(self, timestamp, author, log, file, revision, state):
        self.timestamp = timestamp
        self.author = author
        self.log = log
        self.file = file
        self.revision = revision
        if state == 'dead':
            self.state = FILE_DELETED
        elif revision == '1.1':
            self.state = FILE_ADDED
        else:
            self.state = FILE_MODIFIED

class ChangeSet(object):

    def __init__(self, change):
        self.timestamp = change.timestamp
        self.changes = [change]

    def get_author(self):
        return self.changes[0].author

    def get_log(self):
        return self.changes[0].log

    def get_files(self):
        return map(lambda c: c.file, self.changes)

    author = property(get_author)
    log = property(get_log)
    files = property(get_files)

    def integrate(self, change):
        if change.author != self.author or \
           change.log != self.log or \
           change.file in self.files:
            return False

        if change.timestamp < self.timestamp:
            self.timestamp = change.timestamp

        self.changes.append(change)
        return True

class ChangeSetGenerator(object):

    MAX_TIME_DELTA = 5

    def __init__(self):
        self.changesets = []

    def integrate(self, change):
        # Yield changesets that were opened longer ago than the
        # maximum open time for changesets, relative to the timestamp
        # of the current change.
        changesets = []
        for cs in self.changesets:
            delta = abs(change.timestamp - cs.timestamp)
            if delta >= self.MAX_TIME_DELTA:
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
        changesets = self.changesets
        self.changesets = []
        return changesets
