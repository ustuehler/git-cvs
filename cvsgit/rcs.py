"""RCS interface module for CVSGit."""

from __future__ import absolute_import
import rcsparse

# Some observations about RCS + CVS, although I don't really know
# that much about the RCS format or the CVS usage of it...
#
# 1. The 'branch' keyword is normally absent (or empty?), but has
#    the value "1.1.1" for files that have been imported into the
#    vendor branch and never modified.  The 'head' keyword has the
#    value "1.1" in that case.
#
# 2. When checking out files on trunk via date that were imported
#    in a vendor branch, cvs expands the Id keyword to "1.1.1.1"
#    if the date matches exactly, and to "1.1" if the date is one
#    second or more after the exact date of the import.

import os.path
import sys

from cvsgit.changeset import Change, FILE_ADDED, FILE_MODIFIED, \
    FILE_DELETED

from cvsgit.error import Error
from cvsgit.i18n import _

REV_TIMESTAMP = 1
REV_AUTHOR = 2
REV_STATE = 3
REV_BRANCHES = 4
REV_NEXT = 5
REV_MODE = 6

class RCSError(Error):
    """Base class for exceptions from the cvsgit.rcs module.
    """

class ParseError(RCSError):
    """Raised when an RCS file couldn't be parsed correctly.
    """

    def __init__(self, message, rcsfile):
        """This exception provides additional information.

        'rcsfile' is an RCSFile object.
        """
        super(ParseError, self).__init__(message)
        self.rcsfile = rcsfile

class CheckoutError(ParseError):
    """Extraction of fulltext from RCS file failed.

    This exception indicates that the fulltext of a particular
    revision was requested but couldn't be retrieved from the
    RCS file because the revision does not exist, for example.

    It likely indicates that an invalid argument was passed to
    the RCSFile.blob method.
    """

    def __init__(self, rcsfile, revision):
        """This exception provides additional information.

        'rcsfile' is an RCSFile object.
        'revision' is the revision that couldn't be retrieved.
        """
        super(CheckoutError, self).__init__(
            _("Couldn't retrieve file content for revision %s of %s") % \
                (revision, rcsfile.filename), rcsfile)
        self.revision = revision

class RCSFile(object):
    """Represents a single RCS file.
    """

    def __init__(self, filename, encoding='iso8859-1'):
        """'encoding' sets the encoding assumed of log messages and
        delta text in RCS files.
        """
        self.filename = filename
        self.encoding = encoding
        self.rcsfile = rcsparse.rcsfile(filename)

    head = property(lambda self: self.rcsfile.head)
    branch = property(lambda self: self.rcsfile.branch)
    expand = property(lambda self: self.rcsfile.expand)
    mode = property(lambda self: self.rcsfile.mode)
    revs = property(lambda self: self.rcsfile.revs)

    def revisions(self):
        """Yield all revision numbers from current HEAD backwards.
        """
        if self.branch:
            branchprefix = self.branch + '.'
        else:
            branchprefix = None

        revision = self.head
        while revision != None:
            if branchprefix:
                for brevision in self.revs[revision][REV_BRANCHES]:
                    if brevision.startswith(branchprefix):
                        branchprefix = None
                        revision = brevision
                        break

            yield(revision)
            revision = self.revs[revision][REV_NEXT]

    def changes(self):
        """Yield Change objects for all revisions on HEAD

        The changes are generated by following the current head
        revision back to its origin.  The order of changes is thus
        from most recent to oldest.
        """
        for revision in self.revisions():
            change = self.change(revision)
            if change != None:
                yield(change)

    def change(self, revision):
        """Return a single Change object for <revision>.

        If the revision is 1.1 and has state 'dead' then the file was
        added on a branch and None is returned.
        """
        rev = self.revs[revision]
        if rev[REV_STATE] == 'dead':
            if revision == '1.1':
                # This file was initially added on a branch and so
                # the initial trunk revision was marked 'dead'. We
                # do not count this as a change since it wasn't
                # added and hasn't existed before.
                return None
            else:
                filestatus = FILE_DELETED
        elif rev[REV_NEXT] == None:
            filestatus = FILE_ADDED
        else:
            # XXX: Resurrections of dead revisions aren't flagged
            # as FILE_ADDED.
            filestatus = FILE_MODIFIED

        # The log message for an initial import is actually in
        # the initial vendor branch revision.
        if revision == '1.1' and '1.1.1.1' in rev[REV_BRANCHES]:
            log = self.rcsfile.getlog('1.1.1.1')
        else:
            log = self.rcsfile.getlog(revision)

        # XXX: is this right?
        log = unicode(log, self.encoding)

        if rev[REV_MODE] == None:
            mode = ''
        else:
            mode = rev[REV_MODE]

        return Change(timestamp=rev[REV_TIMESTAMP],
                      author=rev[REV_AUTHOR],
                      log=log,
                      filestatus=filestatus,
                      filename=self.filename,
                      revision=revision,
                      state=rev[REV_STATE],
                      mode=mode)

    def blob(self, revision):
        """Returns the revision's file content.
        """
        try:
            return self.rcsfile.checkout(revision)
        except RuntimeError:
            raise CheckoutError(self, revision)

    # XXX only for debugging; remove later
    def _print_revision(self, revision):
        import time
        rev = self.revs[revision]
        print 'revision:', revision
        print '  timestamp:', time.strftime("%Y-%m-%d %H:%M", time.gmtime(rev[REV_TIMESTAMP]))
        print '  branches:', rev[REV_BRANCHES]
        print '  next:', rev[REV_NEXT]
        print '  state:', rev[REV_STATE]
        print '  log:', self.rcsfile.getlog(revision).splitlines()[0]
