"""Command to compare a Git tree against CVS."""

import re
import subprocess
from subprocess import PIPE
import sys

from cvsgit.cmd import Cmd
from cvsgit.cvs import split_cvs_source
from cvsgit.git import Git
from cvsgit.i18n import _
from cvsgit.utils import Tempdir, stripnl

class verify(Cmd):
    __doc__ = _(
    """Verify the Git work tree against CVS.

    Usage: %prog

    Compares the work tree against a clean checkout from CVS with the
    same timestamp as the HEAD commit.
    """)

    def initialize_options(self):
        self.commit = 'HEAD'

    def finalize_options(self):
        if len(self.args) > 0:
            self.usage_error(_('too many arguments'))

    def run(self):
        self.git = git = Git()

        source = git.config_get('cvs.source')
        if source == None:
            self.fatal(_("'cvs.source' is unset; not a git-cvs repository?"))

        returncode = 0
        with Tempdir() as tempdir:
            date = self.commit_date(self.commit)
            cvsroot, module = split_cvs_source(source)
            command = ['cvs', '-Q', '-d', cvsroot, 'checkout',
                       '-P', '-D', date, '-d', tempdir, module]
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
