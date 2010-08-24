"""CVS-to-Git mapping database for CVSGit."""

import sqlite3

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
              'UNIQUE (file, revision))'

        self.dbh.execute(sql)

    def add_revision(self, revision):
        """Insert an RCS revision into the database.  'revision'
        should be an RCSRevision object."""

        sql = 'INSERT INTO revision (file, revision, timestamp, ' \
              'author, log) VALUES (?,?,?,?,?)'

        assert(revision.rcsfile.filename.endswith(',v'))
        values = (revision.rcsfile.filename[:-2],
                  revision.revision,
                  revision.timestamp,
                  revision.author,
                  revision.log,)

        self.dbh.execute(sql, values)

    def changesets(self):
        # TODO: generate and yield changesets
        return []
