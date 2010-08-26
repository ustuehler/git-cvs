"""Command to clone a CVS repository into a Git repository."""

import os.path
import sys

from cvsgit.cmd import Cmd
from cvsgit.cvs import CVS
from cvsgit.git import Git
from cvsgit.meta import MetaDb
from cvsgit.i18n import _

class clone(Cmd):
    __doc__ = _(
    """Clone a CVS repository or module into a Git repository.

    Usage: %prog <repository> [<directory>]

    Clones an entire CVS repository or module into a Git repository.
    The source argument <repository> is must be a local path pointing
    at the CVS repository root or a module directory within.  The
    destination argument <directory> is selected automatically, based
    on the last component of the source path.
    """)

    def initialize_options(self):
        self.repository = None
        self.directory = None
        self.add_option('--domain', metavar='DOMAIN', help=\
            _("Set the default e-mail domain to use for unknown"
              "CVS committers."))
        self.add_option('--tz', metavar='TIMEZONE', help=\
            _("Set the time zone for dates recorded in RCS files."))
        self.add_option('--incremental', action='store_true', help=\
            _("Leave the partial Git repository around if the clone "
              "command is interruped and attempt to finish a clone "
              "operation that was previously interrupted."))

    def finalize_options(self):
        if len(self.args) < 1:
            self.usage_error(_('missing CVS repository path'))
        elif len(self.args) == 1:
            self.repository = self.args[0]
            self.directory = os.path.basename(self.repository)
        elif len(self.args) == 2:
            self.repository, self.directory = self.args
        else:
            self.usage_error(_('too many arguments'))

    def run(self):
        if os.path.exists(self.directory) and not self.options.incremental:
            self.fatal(_("destination path '%s' already exists") % \
                       self.directory)

        git = Git(self.directory)
        git.init()
        try:
            metadb = MetaDb(git)
            metadb.set_source(self.repository)

            cvs = CVS(metadb)
            cvs.pull_changes()
            cvs.generate_changesets()

            params = {}
            params['tz'] = self.options.tz
            params['domain'] = self.options.domain

            for changeset in cvs.changesets():
                git.import_changeset(changeset, **params)
                cvs.mark_changeset(changeset)
        except:
            if not self.options.incremental:
                git.destroy()
            raise

if __name__ == '__main__':
    clone()
