"""Command to compare a Git tree against CVS."""

import re
import subprocess
from subprocess import PIPE
import sys

from cvsgit.cvs import split_cvs_source
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
        self.add_option('--quiet', action='store_true', help=\
            _("Only report error and warning messages."))

    def finalize_options(self):
        if len(self.args) > 0:
            self.usage_error(_('too many arguments'))

    def run(self):
        conduit = Conduit()
        source = conduit.source
        self.git = git = conduit.git

        returncode = 0
        with Tempdir() as tempdir:
            date = self.commit_date(self.commit)
            cvsroot, module = split_cvs_source(source)
            command = ['cvs', '-Q', '-d', cvsroot, 'checkout',
                       '-P', '-D', date, '-d', tempdir, module]
            if not self.options.quiet:
                print "'%s'" % "' '".join(command)
            subprocess.check_call(command)
            command = ['diff', '-r', tempdir, git.git_work_tree]
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
