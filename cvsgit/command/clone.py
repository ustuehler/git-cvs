"""Command to clone a CVS repository into a Git repository."""

import os.path
import sys
import time

from cvsgit.cmd import Cmd
from cvsgit.cvs import CVS
from cvsgit.git import Git
from cvsgit.meta import MetaDb
from cvsgit.i18n import _

class Progress(object):

    def __init__(self):
        self.last_progress = 0

    def __call__(self, msg, count, total):
        if count == 0 or count == total or \
           time.time() - self.last_progress > 1:
            if count == total:
                print '\r%s: %s' % (msg, _('done'))
            else:
                print '\r%s: %.0f%%' % (msg, count * 100.0 / total),
            sys.stdout.flush()
            self.last_progress = time.time()

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

            params = {}
            params['tz'] = self.options.tz
            params['domain'] = self.options.domain
            params['verbose'] = self.options.verbose

            progress = Progress()
            progress(_('Finding changed files'), 0, 1) # XXX
            cvs.pull_changes(onprogress=lambda count, total:
                progress(_('Pulling changes from CVS'), count, total))
            cvs.generate_changesets(onprogress=lambda count, total:
                progress(_('Calculating changets'), count, total))
            cvs.export_changesets(git, params, onprogress=lambda count, total:
                progress(('Importing changesets'), count, total))
        except:
            if not self.options.incremental:
                git.destroy()
            raise

if __name__ == '__main__':
    clone()
