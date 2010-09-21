"""Main application class and user interface helper routines for
'git-cvs'."""

import sys
import time

import cvsgit.cmd
from cvsgit.git import Git
from cvsgit.cvs import CVS
from cvsgit.meta import MetaDb
from cvsgit.i18n import _

Command = cvsgit.cmd.Cmd

class Progress(object):
    """Display progress information."""

    def __init__(self, message, enabled=True):
        self.message = message
        self.enabled = enabled
        self.last_progress = 0

    def __call__(self, count, total):
        if not self.enabled:
            return
        if count == 0 or count == total or \
           time.time() - self.last_progress > 1:
            if count == total:
                print '\r%s: %s (%d/%d)' % \
                    (self.message, _('done.'), count, total)
            else:
                print '\r%s: %3.0f%% (%d/%d)' % \
                    (self.message, count * 100.0 / total, count, total),
            sys.stdout.flush()
            self.last_progress = time.time()

class GitCVS(object):

    def __init__(self):
        self.git = Git()
        self.metadb = MetaDb(self.git)
        self.cvs = CVS(self.metadb)

    def fetch(self, onprogress=True):
        _onprogress = onprogress
        if _onprogress is True:
            _onprogress = Progress(_('Parsing RCS files'))

        self.cvs.pull_changes(onprogress=_onprogress)

        _onprogress = onprogress
        if _onprogress is True:
            _onprogress = Progress(_('Calculating changesets'))

        self.cvs.generate_changesets(onprogress=_onprogress)

        _onprogress = onprogress
        if _onprogress is True:
            _onprogress = Progress(_('Importing changesets'))

        self.cvs.export_changesets(self.git,
                                   {'branch':'refs/remotes/git-cvs'},
                                   onprogress=_onprogress)
