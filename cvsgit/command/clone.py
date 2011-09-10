"""Command to clone a CVS repository or module as a Git repository."""

import os.path
import shutil

from cvsgit.main import Command, Conduit
from cvsgit.i18n import _

class clone(Command):
    __doc__ = _(
    """Clone a CVS repository or module into a Git repository.

    Usage: %prog [options] <repository> [<directory>]

    Clones an entire CVS repository or a module into a Git repository.
    The source argument <repository> must be a local path pointing at
    the CVS repository root or a module directory within.  The
    destination argument <directory> is selected automatically, based
    on the last component of the source path.
    """)

    def initialize_options(self):
        self.repository = None
        self.directory = None
        self.add_option('--bare', action='store_true', help=\
            _("Create a bare Git repository without work tree."))
        self.add_option('--limit', type='int', metavar='COUNT', help=\
            _("Stop importing after COUNT new commits."))
        self.add_option('--domain', metavar='DOMAIN', help=\
            _("Set the e-mail domain to use for unknown authors."))
        self.add_option('--partial', action='store_true', help=\
            _("Keep the incomplete Git repository if this command "
              "is interrupted by the user or an unexpected error "
              "and continue from the last checkpoint if the Git "
              "repository already exists."))
        self.add_option('--fast-import-dump', action='store_true', help=\
            _("Write all changesets to stdout in git-fast-import(1) "
              "format but do not actually import them.  This option "
              "is mostly useful for debugging."))
        self.add_option('--quiet', action='store_true', help=\
            _("Only report error and warning messages."))
        self.add_option('--verbose', action='store_true', help=\
            _("Display each changeset as it is imported."))

    def finalize_options(self):
        if len(self.args) < 1:
            self.usage_error(_('missing CVS repository path'))
        elif len(self.args) == 1:
            self.repository = os.path.abspath(self.args[0])
            self.directory = os.path.basename(self.repository)
        elif len(self.args) == 2:
            self.repository, self.directory = self.args
        else:
            self.usage_error(_('too many arguments'))

    def run(self):
        if os.path.exists(self.directory) and not self.options.partial:
            self.fatal(_("destination path '%s' already exists") % \
                       self.directory)

        conduit = Conduit(self.directory)
        conduit.init(self.repository,
                     bare=self.options.bare,
                     domain=self.options.domain,
                     quiet=self.options.quiet)
        try:
            conduit.fetch(limit=self.options.limit,
                          quiet=self.options.quiet,
                          verbose=self.options.verbose,
                          fast_import_dump=self.options.fast_import_dump)

            if not self.options.bare and not self.options.fast_import_dump:
                conduit.git.checkout('-b', 'master', conduit.branch)
        except:
            if not self.options.partial:
                shutil.rmtree(self.directory)
            raise

if __name__ == '__main__':
    clone()
