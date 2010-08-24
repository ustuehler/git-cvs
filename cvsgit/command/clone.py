"""Command to clone a CVS repository into a Git repository."""

import os.path
import sys

from cvsgit.cmd import Cmd
from cvsgit.cvs import CVSROOT
from cvsgit.db import Db
from cvsgit.git import Git

class StatusLine(object):
    def __init__(self, width=72):
        self.width = width
        self.line = ''

    def abbrev(self, line):
        # Use up one less character column than available because some
        # terminals will wrap to the next line if ther cursor advances
        # past the end of the line.
        if len(line) < self.width:
            return line
        else:
            return line[:self.width-1]

    def begin(self, line=''):
        print '\r' + self.abbrev(line),
        sys.stdout.flush()
        self.line = line

    def erase(self):
        print '\r' + (' ' * len(self.line)),
        sys.stdout.flush()
        self.line = ''

    def update(self, line=None):
        if line is None: line = self.line
        self.erase()
        self.begin(line)

    def finish(self, line=None):
        if not line is None:
            self.update(line)
        print ''

class clone(Cmd):
    """Clone a CVS repository into a Git repository.

    Usage: %prog <repository> [<directory>]

    Clone an entire CVS repository or module into a Git repository.
    The source argument <repository> is must be a local path pointing
    at the CVS repository root or a module directory within.  The
    destination argument <directory> is selected automatically, based
    on the last component of the source path.
    """

    def initialize_options(self):
        self.repository = None
        self.directory = None

    def finalize_options(self):
        if len(self.args) < 1:
            self.usage_error('missing CVS repository path')
        elif len(self.args) == 1:
            self.repository = self.args[0]
            self.directory = os.path.basename(self.repository)
        elif len(self.args) == 2:
            self.repository, self.directory = self.args
        else:
            self.usage_error('too many arguments')

    def run(self):
        status = StatusLine()
        git = Git(self.directory)
        git.init()
        try:
            db = Db(os.path.join(git.git_dir, 'cvsgit.db'))
            cvs = CVSROOT(self.repository)

            status.nfiles = 0
            status.nrevisions = 0

            def progress(status):
                status.nfiles += 1
                status.update('Indexing CVS repository... ' \
                              '(%d files, %d revisions)' % \
                              (status.nfiles, status.nrevisions))

            status.begin('Indexing CVS repository...')
            for revision in cvs.revisions(onrcsfile=lambda ignore:
                                              progress(status)):
                status.nrevisions += 1
                db.add_revision(revision)
            status.finish('Indexing CVS repository...done')

            status.begin('Generating changesets...')
            for changeset in db.changesets():
                git.add_changeset(changeset)
            status.finish('Indexing CVS repository...done')
        except:
            status.finish()
            git.destroy()
            raise

if __name__ == '__main__':
    clone()
