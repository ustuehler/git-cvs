"""Command to clone a CVS repository into a Git repository."""

import os.path
import sys

from cvsgit.cmd import Cmd
from cvsgit.cvs import CVSROOT
from cvsgit.db import Db
from cvsgit.git import Git
from cvsgit.i18n import _

class clone(Cmd):
    __doc__ = _("""Clone a CVS repository or module into a Git repository.

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
        self.add_option('--domain', metavar='DOMAIN',
            default='local', help=\
            _("Set the default e-mail domain to use for unknown"
              "CVS committers."))
        self.add_option('--tz', metavar='TIMEZONE', help=\
            _("Set the time zone for dates recorded in RCS files."))
        self.add_option('--no-cleanup', action='store_true', help=\
            _("Don't delete the partial Git repository on error."))

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
        if os.path.exists(self.directory):
            self.fatal(_("destination path '%s' already exists") % \
                       self.directory)

        git = Git(self.directory)
        git.init()
        try:
            db = Db(os.path.join(git.git_dir, 'cvsgit.db'))
            cvs = CVSROOT(self.repository)

            try:
                print 'Parsing RCS revisions...'
                for revision in cvs.revisions():
                    db.add_revision(revision)
            finally:
                db.commit()

            gfi = git.fast_import(domain=self.options.domain,
                                  tz=self.options.tz)
            try:
                print 'Generating changesets...'
                for changeset in db.changesets():
                    gfi.commit(cvs, changeset)
                gfi.close()
            except:
                try:
                    gfi.close()
                except Exception, (e):
                    print '%s: warning: %s' % (self.option_parser.prog, e)
                raise
        except:
            if not self.options.no_cleanup:
                git.destroy()
            raise

if __name__ == '__main__':
    clone()
