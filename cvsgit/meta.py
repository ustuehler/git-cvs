"""Metadata for CVSGit about a pair of CVS and Git repositories."""

import os.path
import re
import sqlite3

from cvsgit.changeset import Change, ChangeSet
from cvsgit.i18n import _

class MetaDb(object):
    """Database containing metadata about a pair of CVS and Git
    repositories.  The actual metadata is distributed at least across
    an SQLite database and Git's config file, both in GIT_DIR."""

    # As of now the database contains only revisions from the CVS
    # repository that are pending to be grouped into changesets.

    def __init__(self, git):
        self.git = git
        self._source = None
        self._dbh = None

    def get_source(self):
        if self._source is None:
            self._source = git.config_get('cvsgit.source')
            if self._source is None:
                raise RuntimeError, \
                    _("missing 'cvsgit.source' in Git config")
        return self._source

    def set_source(self, source):
        self.git.config_set('cvsgit.source', source)
        self._source = source

    source = property(get_source, set_source)

    def get_dbh(self):
        if self._dbh is None:
            filename = os.path.join(self.git.git_dir, 'cvsgit.db')
            dbh = sqlite3.connect(filename)

            # Create the table that contains changes pulled from CVS.
            #
            # 'changeset_id' is NULL until a change is associated with
            # a complete changeset.
            sql = 'CREATE TABLE IF NOT EXISTS change (' \
                  'timestamp DATETIME NOT NULL, ' \
                  'author VARCHAR NOT NULL, ' \
                  'log TEXT NOT NULL, ' \
                  'filestatus CHAR(1) NOT NULL, ' \
                  'filename VARCHAR NOT NULL, ' \
                  'revision VARCHAR NOT NULL, ' \
                  'state VARCHAR(8) NOT NULL, ' \
                  'mode CHAR(1) NOT NULL, ' \
                  'changeset_id INTEGER, ' \
                  'PRIMARY KEY (filename, revision))'
            dbh.execute(sql)
            sql = 'CREATE INDEX IF NOT EXISTS change__changeset_id ' \
                  'ON change (changeset_id)'
            dbh.execute(sql)

            # Create the table that defines the attributes of complete
            # changesets.  'id' will be referenced by one or more rows
            # in the 'change' table.
            sql = 'CREATE TABLE IF NOT EXISTS changeset (' \
                  'id INTEGER PRIMARY KEY, ' \
                  'start_time DATETIME NOT NULL, ' \
                  'end_time DATETIME NOT NULL, ' \
                  'mark VARCHAR)'
            dbh.execute(sql)
            sql = 'CREATE UNIQUE INDEX IF NOT EXISTS ' \
                  'changeset__id__start_time__mark ' \
                  'ON changeset (id, start_time, mark)'
            dbh.execute(sql)

            # Create the table that stores stat() information for all
            # paths in the CVS repository.  This allows the CVS change
            # scanner to skip unmodified RCS files and directories.
            sql = 'CREATE TABLE IF NOT EXISTS statcache (' \
                  'path VARCHAR PRIMARY KEY, ' \
                  'mtime INTEGER NOT NULL, ' \
                  'size INTEGER NOT NULL)'
            dbh.execute(sql)

            self._dbh = dbh
        return self._dbh
    
    dbh = property(get_dbh)

    def load_statcache(self):
        """Load the complete stat() cache and return it as a dictionary
        of the form {path:(mtime, size)}."""

        sql = 'SELECT path, mtime, size FROM statcache'
        statcache = {}
        for row in self.dbh.execute(sql):
            statcache[row[0]] = row[1:]
        return statcache

    def update_statcache(self, statcache):
        """'statcache' is a dictionary of {path:(mtime, size)} to insert
        into or update in the meta database's stat() cache."""

        sql = 'INSERT OR REPLACE INTO statcache ' \
              '(path, mtime, size) VALUES (?,?,?)'
        for path in statcache.keys():
            values = (path,) + statcache[path]
            self.dbh.execute(sql, values)

    def add_change(self, change):
        """Insert a single file change into the database.

        If a record for the specified file and revision exists it is
        assumed to be identical and the change will be ignored.

        Note that multiple updates to the database may be grouped into
        a larger transaction for performance, but the caller can use
        commit() to ensure that the changes get flushed to disk."""

        sql = 'INSERT OR IGNORE INTO change ' \
              '(timestamp, author, log, filestatus, filename, ' \
              'revision, state, mode) VALUES (?,?,?,?,?,?,?,?)'
        values = (change.timestamp,
                  change.author,
                  change.log,
                  change.filestatus,
                  change.filename,
                  change.revision,
                  change.state,
                  change.mode,)
        self.dbh.execute(sql, values)

    def add_changeset(self, changeset):
        """Record the attributes of 'changeset' and mark the
        referenced changes as belonging to this changeset.

        Associating changes with a changeset is guaranteed to be
        atomic.  The update will be performed in a transaction which
        is rolled back if the process is somehow interrupted."""

        # Begin a fresh transaction.
        self.dbh.commit()
        try:
            sql = 'INSERT INTO changeset (start_time, end_time) ' \
                  'VALUES (?,?)'
            values = (changeset.start_time,
                      changeset.end_time,)
            id = self.dbh.execute(sql, values).lastrowid

            sql = 'UPDATE change SET changeset_id=%s '\
                  'WHERE filename=? AND revision=?' % id
            self.dbh.executemany(sql,
                map(lambda c: (c.filename, c.revision),
                    changeset.changes))

            # Commit this transaction.
            self.dbh.commit()
        except:
            self.dbh.rollback()
            raise

    def mark_changeset(self, changeset):
        """Mark 'changeset' as having been integrated."""

        assert(changeset.id != None)
        sql = 'UPDATE changeset SET mark=? WHERE id=?'
        self.dbh.execute(sql, (changeset.mark, changeset.id,))
        self.dbh.commit()

    def commit(self):
        """Commit the pending database transaction, if any."""

        self.dbh.commit()

    def count_changes(self):
        "Return the number of free changes (not bound in a changeset)."

        sql = 'SELECT COUNT(*) FROM change WHERE changeset_id IS NULL'
        return self.dbh.execute(sql).fetchone()[0]

    def changes_by_timestamp(self):
        """Yield a list of free changes recorded in the database and
        not bound to a changeset, ordered by their timestamp."""

        sql = 'SELECT timestamp, author, log, filestatus, filename, ' \
              'revision, state, mode FROM change WHERE changeset_id IS ' \
              'NULL ORDER BY timestamp'
        for row in self.dbh.execute(sql):
            yield(Change(timestamp=row[0],
                         author=row[1],
                         log=row[2],
                         filestatus=row[3],
                         filename=row[4],
                         revision=row[5],
                         state=row[6],
                         mode=row[7]))

    def count_changesets(self):
        "Return the number of unmarked changesets (not imported)."

        sql = 'SELECT COUNT(*) FROM changeset WHERE mark IS NULL'
        return self.dbh.execute(sql).fetchone()[0]

    def _select_changesets(self, where):

        where = where % {'changeset':'cs'}
        sql = """SELECT cs.id, cs.start_time, cs.end_time,
                        c.timestamp, c.author, c.log,
                        c.filestatus, c.filename,
                        c.revision, c.state, c.mode
                 FROM changeset cs
                 INNER JOIN change c ON c.changeset_id = cs.id
                 WHERE %s
                 ORDER BY cs.start_time, cs.id""" % where

        changeset = None
        for row in self.dbh.execute(sql):
            change = Change(timestamp=row[3],
                            author=row[4],
                            log=row[5],
                            filestatus=row[6],
                            filename=row[7],
                            revision=row[8],
                            state=row[9],
                            mode=row[10])

            if changeset is None or changeset.id != row[0]:
                if changeset:
                    yield(changeset)

                changeset = ChangeSet(change, id=row[0])
                changeset.provider = self
                changeset.start_time = row[1]
                changeset.end_time = row[2]
            else:
                changeset.changes.append(change)

        if changeset:
            yield(changeset)

    def head_changeset(self):
        """Return the "head" changeset, the one with the highest value
        of 'id' ('mark' is ignored) or None if there is no changeset."""

        where = '%(changeset)s.id IS MAX(%(changeset)s.id)'
        for cs in self._select_changesets(where):
            return cs

    def changesets_by_start_time(self):
        """Yield a list of all unmarked changesets currently recorded
        in the database, ordered by their start time."""

	where = '%(changeset)s.mark IS NULL'
        return self._select_changesets(where)
