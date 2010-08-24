"""RCS interface module for CVSGit."""

import os.path
import rcsparse

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

    def __init__(self, filename, prefix=''):
        """'prefix' is a path prefix to prepend to 'filename' when
        accessing the file.  This allows 'filename' to be a relative
        path, relative to a CVS repository root, for example."""
        self.filename = filename
        self.prefix = prefix

    def revisions(self):
        "Yield all revisions in the RCS file."
        f = file(os.path.join(self.prefix, self.filename), 'r')
        try:
            self.parsed = {}
            rcsparse.parse(f, self)
            revisions = self.parsed.values()
            del self.parsed

            for revision in revisions:
                yield(RCSRevision(self, *revision))
        finally:
            f.close()

    def define_revision(self, revision, timestamp, author, state,
                        branches, next):
        "Part of the RCS parser callback interface."
        assert(not self.parsed.has_key(revision))
        self.parsed[revision] = [revision, timestamp, author, state,
                                 branches, next]

    def set_revision_info(self, revision, log, text):
        "Part of the RCS parser callback interface."
        assert(self.parsed.has_key(revision))
        self.parsed[revision] += [log, text]
