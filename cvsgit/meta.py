"""Metadata for CVSGit about a pair of CVS and Git repositories."""

import os.path
import re
import sqlite3

from cvsgit.changeset import Change, ChangeSet
from cvsgit.i18n import _

class MetaDb(object):
    """Database of CVS revisions (changes) and combined changesets.

    The database contains revisions from the CVS repository that are
    pending or already grouped into changesets and a mark indicating
    whether a changeset was already processed.  For Git, the mark is
    the SHA1 commit hash.  Unprocessed changesets have the mark None.
    """

    def __init__(self, filename):
        self.filename = filename
        self._dbh = None

    def get_dbh(self):
        if self._dbh is None:
            dbh = sqlite3.connect(self.filename)

            # http://web.utk.edu/~jplyon/sqlite/SQLite_optimization_FAQ.html
            dbh.execute("PRAGMA synchronous=OFF")
            dbh.execute("PRAGMA count_changes=OFF")
            #dbh.execute("PRAGMA cache_size=4000")

            # This should also help, but causes the behaviour of the
            # ROLLBACK command to become undefined.
            dbh.execute("PRAGMA journal_mode=OFF")

            # This helps for the temporary table which we create when
            # iterating over changes for changeset generation, but
            # bloats the process image a lot.
            #dbh.execute("PRAGMA temp_store=MEMORY")

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
            dbh.execute("""
                CREATE INDEX IF NOT EXISTS change__timestamp
                ON change (timestamp)""")

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
            dbh.execute("""
                CREATE TABLE IF NOT EXISTS statcache (
                    path VARCHAR PRIMARY KEY,
                    mtime INTEGER NOT NULL,
                    size INTEGER NOT NULL)""")
            # With this index, I haven't observed any speed gain.
            #dbh.execute("""
            #    CREATE INDEX IF NOT EXISTS statcache_index
            #    ON statcache (path, mtime, size)""")

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
        commit() to ensure that the changes get flushed to disk.
        """
        self.dbh.execute("""
            INSERT OR IGNORE INTO change
                (timestamp, author, log, filestatus, filename,
                revision, state, mode)
            VALUES (?,?,?,?,?,?,?,?)""",
            (change.timestamp, change.author, change.log,
             change.filestatus, change.filename, change.revision,
             change.state, change.mode,))

    def add_changeset(self, changeset):
        """Record the attributes of 'changeset' and mark the
        referenced changes as belonging to this changeset.

        Associating changes with a changeset can be considered an
        atomic operation from the caller's perspective.
        """
        id = self.dbh.execute("""
            INSERT INTO changeset (start_time, end_time) VALUES (?,?)
            """, (changeset.start_time, changeset.end_time,)).lastrowid
        try:
            self.dbh.executemany("""
                UPDATE change SET changeset_id=%d
                WHERE filename=? AND revision=?
                """ % id, map(lambda c: (c.filename, c.revision),
                              changeset.changes))
        except:
            self.dbh.execute("""
                UPDATE change SET changeset_id=NULL
                WHERE changeset_id=%dfilename=? AND revision=?
                """ % id)
            raise

    def mark_changeset(self, changeset):
        """Mark 'changeset' as having been integrated.
        """
        assert(changeset.id != None)
        sql = 'UPDATE changeset SET mark=? WHERE id=?'
        self.dbh.execute(sql, (changeset.mark, changeset.id,))

    def begin_transaction(self):
        """Starts a new transaction (disables autocommit).
        """
        self.dbh.execute('BEGIN TRANSACTION')

    def commit(self):
        """Commits the current transaction.
        """
        self.dbh.commit()

    def end_transaction(self):
        """Ends a new transaction (enables autocommit).
        """
        self.dbh.execute('END TRANSACTION')

    def count_changes(self):
        """Return the number of free changes (not bound in a changeset).
        """
        return self.dbh.execute("""
            SELECT COUNT(*)
            FROM change
            WHERE changeset_id IS NULL""").fetchone()[0]

    def changes_by_timestamp(self, processed=None, reentrant=True):
        """Yields a list of changes recorded in the database.

        The 'processed' keyword determines wheather changes which are
        already included in a changeset are to be included or not.  If
        the value is neuter True nor False, all changes are included.
        """
        if processed == True:
            where = 'changeset_id IS NOT NULL'
        elif processed == False:
            where = 'changeset_id IS NULL'
        else:
            where = '1'

        def mkchange(row):
            return Change(timestamp=row[0], author=row[1], log=row[2],
                          filestatus=row[3], filename=row[4],
                          revision=row[5], state=row[6], mode=row[7])

        if not reentrant:
            for row in self.dbh.execute("""
                SELECT timestamp, author, log, filestatus, filename,
                       revision, state, mode
                FROM change
                WHERE %s
                ORDER BY timestamp""" % where):
                yield(mkchange(row))
            return

        self.dbh.execute("""
            CREATE TEMPORARY TABLE free_change AS
            SELECT timestamp, author, log, filestatus, filename,
                   revision, state, mode
            FROM change
            LIMIT 0""")
        self.dbh.execute("""
            CREATE INDEX free_change__timestamp
            ON free_change (timestamp)""")
        self.dbh.execute("""
            CREATE INDEX free_change__filename__revision
            ON free_change (filename, revision)""")
        self.dbh.execute("""
            INSERT INTO free_change
            SELECT timestamp, author, log, filestatus, filename,
                   revision, state, mode
            FROM change
            WHERE %s""" % where)

        try:
            while True:
                rows = self.dbh.execute("""
                    SELECT timestamp, author, log, filestatus, filename,
                           revision, state, mode
                    FROM free_change
                    ORDER BY timestamp
                    LIMIT 1000""").fetchall()
                if len(rows) == 0:
                    break
                for row in rows:
                    change = mkchange(row)
                    yield(change)
                    self.dbh.execute("""
                        DELETE FROM free_change
                        WHERE filename = ? AND revision = ?""",
                        (change.filename, change.revision,))
        finally:
            self.dbh.execute('DROP TABLE IF EXISTS free_change')

    def count_changesets(self):
        """Return the number of unmarked changesets (not imported).
        """
        sql = 'SELECT COUNT(*) FROM changeset WHERE mark IS NULL'
        return self.dbh.execute(sql).fetchone()[0]

    def _select_changesets(self, where):
        where = where % {'changeset':'cs'}
        sql = """
            SELECT cs.id, cs.start_time, cs.end_time, c.timestamp,
                   c.author, c.log, c.filestatus, c.filename,
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
        of 'id' ('mark' is ignored) or None if there is no changeset.
        """
        where = '%(changeset)s.id IS MAX(%(changeset)s.id)'
        for cs in self._select_changesets(where):
            return cs

    def changesets_by_start_time(self):
        """Yield a list of all unmarked changesets currently recorded
        in the database, ordered by their start time.
        """
	where = '%(changeset)s.mark IS NULL'
        return self._select_changesets(where)
