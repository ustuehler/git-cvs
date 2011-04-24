"""Command to initialize a Git repository with all the required
meta-data for 'git-cvs'."""

import os.path
import sys
import time

from cvsgit.cmd import Cmd
from cvsgit.cvs import CVS
from cvsgit.git import Git
from cvsgit.meta import MetaDb
from cvsgit.i18n import _

class init(Cmd):
    __doc__ = _(
    """Initialize a Git repository to track a CVS repository.

    Usage: %prog [options] <repository> [directory]

    Initializes a Git repository and sets up the required meta-data to
    track a CVS repository.  The 'repository' argument must be a local
    file system path pointing at the actual root of a CVS repository
    or at any module directory within the repository.

    If 'directory' is omitted, the current working directory will be
    initialized instead of the one specified.
    """)

    def initialize_options(self):
        self.repository = None
        self.add_option('--bare', action='store_true', help=\
            _("Initialize a bare repository. See git-init(1)."))
        self.add_option('--domain', metavar='DOMAIN', help=\
            _("Set the 'cvs.domain' configuration option to the "
              "e-mail domain to use as a default value for unknown "
              "authors."))

    def finalize_options(self):
        if len(self.args) < 1:
            self.usage_error(_('missing CVS repository path'))
        elif len(self.args) == 1:
            self.repository = self.args[0]
            self.directory = None
        elif len(self.args) == 2:
            self.repository = self.args[0]
            self.directory = self.args[1]
        else:
            self.usage_error(_('too many arguments'))

    def run(self):
        git = Git(self.directory, bare=self.options.bare)
        git.init()
        git.config_set('cvs.source', self.repository)

        if self.options.domain:
            git.config_set('cvs.domain', self.options.domain)

if __name__ == '__main__':
    init()
