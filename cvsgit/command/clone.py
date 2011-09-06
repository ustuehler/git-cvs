"""Command to clone a CVS repository or module as a Git repository."""

import os.path
import sys
import time

from cvsgit.cmd import Cmd
from cvsgit.cvs import CVS
from cvsgit.git import Git
from cvsgit.meta import MetaDb
from cvsgit.i18n import _

class Progress(object):

    def __init__(self, enabled):
        self.enabled = enabled
        self.last_progress = 0

    def __call__(self, msg, count, total):
        if not self.enabled:
            return
        if count == 0 or count == total or \
           time.time() - self.last_progress > 1:
            if count == total:
                print '\r%s: %s (%d/%d)' % \
                    (msg, _('done.'), count, total)
            else:
                print '\r%s: %3.0f%% (%d/%d)' % \
                    (msg, count * 100.0 / total, count, total),
            sys.stdout.flush()
            self.last_progress = time.time()

class clone(Cmd):
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
        self.add_option('--count', metavar='COUNT', help=\
            _("Stop importing after COUNT new commits."))
        self.add_option('--domain', metavar='DOMAIN', help=\
            _("Set the e-mail domain to use for unknown authors."))
        self.add_option('--incremental', action='store_true', help=\
            _("Keep the incomplete Git repository if this command "
              "is interrupted and continue from the last checkpoint "
              "if the Git repository exists in the beginning."))
        self.add_option('--progress', action='store_true', help=\
            _("Display a progress meter."))
        self.add_option('--quiet-git', action='store_true', help=\
            _("Turn off informational messages from Git."))
        self.add_option('--verbose', action='store_true', help=\
            _("Display each changeset as it is imported."))

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

        if self.options.count:
            self.options.count = int(self.options.count)

    def run(self):
        if os.path.exists(self.directory) and not self.options.incremental:
            self.fatal(_("destination path '%s' already exists") % \
                       self.directory)

        git = Git(self.directory)
        git.init(quiet=self.options.quiet_git)
        try:
            metadb = MetaDb(git)
            metadb.set_source(self.repository)
            cvs = CVS(metadb)

            params = {}
            params['domain'] = self.options.domain
            params['verbose'] = self.options.verbose

            progress = Progress(self.options.progress)
            progress(_('Counting files'), 0, 1) # XXX
            cvs.pull_changes(onprogress=lambda count, total:
                progress(_('Parsing RCS files'), count, total))
            cvs.generate_changesets(onprogress=lambda count, total:
                progress(_('Calculating changesets'), count, total))
            cvs.export_changesets(git, params, onprogress=lambda count, total:
                progress(_('Importing changesets'), count, total),
                count=self.options.count)
            if not git.is_bare():
                git.checkout()
        except:
            if not self.options.incremental:
                git.destroy()
            raise

if __name__ == '__main__':
    clone()
