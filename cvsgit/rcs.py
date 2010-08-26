"""RCS interface module for CVSGit."""

import os.path

from cvsgit.changeset import Change, FILE_ADDED, FILE_MODIFIED, \
    FILE_DELETED

# Our 'rcsparse' module is actually a simple copy of the RCS parser
# code from cvs2svn.
from cvsgit import rcsparse

class RCSRevision(object):
    "Represents a single RCS revision in an RCS file."

    def __init__(self, rcsfile, revision, timestamp, author, state,
                 branches, next, log, text):
        self.rcsfile = rcsfile
        self.revision = revision
        self.timestamp = timestamp
        self.author = author
        self.state = state
        self.branches = branches
        self.next = next
        self.log = log
        self.text = text

class RCSFile(rcsparse.Sink):
    "Represents a single RCS file."

    def __init__(self, filename, encoding='iso8859-1'):
        """'encoding' sets the encoding of log messages and delta text
        in RCS files."""
        self.filename = filename
        self.encoding = encoding

    def changes(self):
        """Return the list of Change objects corresponding to all
        revisions defined in this RCS file. The order of changes is
        arbitrary."""

        f = file(os.path.join(self.filename), 'r')
        try:
            self.change = {}
            rcsparse.parse(f, self)
            changes = self.change.values()
            del self.change
            return changes
        finally:
            f.close()

    def define_revision(self, revision, timestamp, author, state,
                        branches, next):
        "Part of the RCS parser callback interface."

        # XXX: looks ugly; there must be a better way?
        if state == 'dead':
            state = FILE_DELETED
        elif revision == '1.1':
            state = FILE_ADDED
        else:
            state = FILE_MODIFIED

        assert(not self.change.has_key(revision))
        self.change[revision] = Change(timestamp=timestamp,
                                       author=author,
                                       log=None,
                                       filename=self.filename,
                                       revision=revision,
                                       state=state)

    def set_revision_info(self, revision, log, text):
        "Part of the RCS parser callback interface."

        assert(self.change.has_key(revision))
        self.change[revision].log = unicode(log, self.encoding)
