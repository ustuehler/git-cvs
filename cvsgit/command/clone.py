"""Command to clone a CVS repository or module as a Git repository."""

import os.path
import shutil

from cvsgit.main import Command, Conduit
from cvsgit.i18n import _
from cvsgit.command.verify import Verify

class Clone(Command):
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
        self.add_option('--verify', action='store_true', help=\
            _("Run the verify command after cloning (does not work "
              "with --bare)."))
        self.add_option('--no-repack', action='store_true', help=\
            _("Don't run \"git repack -adF\" after cloning (so you "
              "end up with an uncompressed pack file)."))
        self.add_quiet_option()
        self.add_verbose_option()
        self.add_authors_option()
        self.add_stop_on_unknown_author_option()

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

        self.finalize_authors_option()

    def run(self):
        if os.path.exists(self.directory):
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
                          authors=self.options.authors,
                          stop_on_unknown_author=\
                              self.options.stop_on_unknown_author)

            git = conduit.git

            if not self.options.no_repack:
                git.check_command('repack', '-adF')

            head_branch = git.symbolic_ref('HEAD')
            if head_branch == 'refs/heads/master':
                if self.options.bare:
                    git.check_command('branch', '-f', 'master', conduit.branch)
                else:
                    git.check_command('reset', '-q', '--hard', conduit.branch)
        except:
            shutil.rmtree(self.directory)
            raise

        # Verify after the above rmtree, because someone likely wants
        # to inspect the repository if the verification fails.
        if self.options.verify:
            try:
                olddir = os.getcwd()
                os.chdir(git.git_work_tree)
                Verify().eval()
            finally:
                os.chdir(olddir)
