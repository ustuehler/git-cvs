"""Command to clone a CVS repository into a Git repository."""

import os.path
import sys

from cvsgit.cmd import Cmd
from cvsgit.cvs import CVSROOT
from cvsgit.db import Db
from cvsgit.git import Git

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
        git = Git(self.directory)
        git.init()
        try:
            db = Db(os.path.join(git.git_dir, 'cvsgit.db'))
            cvs = CVSROOT(self.repository)

            for revision in cvs.revisions():
                db.add_revision(revision)

            for changeset in db.changesets():
                git.add_changeset(changeset)
        except:
            git.destroy()
            raise

if __name__ == '__main__':
    clone()
