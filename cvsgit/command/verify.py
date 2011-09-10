"""Command to compare a Git tree against CVS."""

import re
import subprocess
from subprocess import PIPE
import sys

from cvsgit.cvs import split_cvs_source
from cvsgit.git import GitCommandError
from cvsgit.i18n import _
from cvsgit.main import Command, Conduit
from cvsgit.utils import Tempdir, stripnl

class verify(Command):
    __doc__ = _(
    """Verify the Git work tree against CVS.

    Usage: %prog

    Compares the work tree against a clean checkout from CVS with the
    same timestamp as the HEAD commit.
    """)

    def initialize_options(self):
        self.commit = 'HEAD'
        self.add_option('--history', action='store_true', help=\
            _("Walk backwards through the entire history."))
        self.add_option('--quiet', action='store_true', help=\
            _("Only report error and warning messages."))

    def finalize_options(self):
        if len(self.args) > 0:
            self.usage_error(_('too many arguments'))

    def run(self):
        conduit = Conduit()
        self.cvsroot, self.module = split_cvs_source(conduit.source)
        self.git = git = conduit.git
        with Tempdir() as tempdir:
            self.tempdir = tempdir

            while True:
                returncode = self._run()
                if returncode != 0:
                    return returncode
                elif not self.options.history:
                    return 0

                try:
                    self.git.checkout('-q', 'HEAD~1')
                except GitCommandError:
                    return 0

    def _run(self):
        returncode = 0
        date = self.commit_date(self.commit)
        head = self.git.rev_parse('--short', 'HEAD')
        command = ['cvs', '-Q', '-d', self.cvsroot, 'checkout',
                   '-P', '-D', date, '-d', self.tempdir, self.module]
        if not self.options.quiet:
            print "(%s) '%s'" % (head, "' '".join(command))
        subprocess.check_call(command)
        command = ['diff', '-r', self.tempdir, self.git.git_work_tree]
        pipe = subprocess.Popen(command, stdout=PIPE, stderr=PIPE)
        stdout, dummy = pipe.communicate()
        for line in stripnl(stdout).split('\n'):
            if re.match('^Only in .+: \.git$', line):
                continue
            if re.match('^Only in .+: CVS$', line):
                continue
            if not self.options.quiet:
                sys.stdout.write(line + '\n')
            returncode = 1
        return returncode

    def commit_date(self, commit):
        """Get the commit date as a string in UTC timezone.
        """
        command = ['git', 'log', '-1', commit]
        pipe = self.git._popen(command, stdout=PIPE, stderr=PIPE)
        stdout, stderr = pipe.communicate()
        if pipe.returncode != 0:
            self.fatal(_("can't get commit date of %s" % commit))
        match = re.search('Date: +[^ ]+ (.*) \+0000', stdout)
        if match:
            return match.group(1)
        else:
            self.fatal(_("couldn't match Date: in output of '%s'") % \
                           ' '.join(command))

if __name__ == '__main__':
    verify()
