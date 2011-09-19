"""Command to show diff output more like CVS would do."""

import re
import subprocess
import sys

from cvsgit.main import Command, Conduit
from cvsgit.i18n import _

class Diff(Command):
    __doc__ = _(
    """Show changes, but more like CVS would output them

    Usage: %prog [options] [<commit>]

    Show changes between the working tree and the index, or the
    changes in a given <commit>.  Eventually this command should
    behave much like git-diff(1), but the output should be more
    like the output of cvs(1).
    """)

    def initialize_options(self):
        pass

    def finalize_options(self):
        if len(self.args) > 1:
            self.usage_error(_('too many arguments'))
        elif len(self.args) == 1:
            self.commit = self.args[0]
        else:
            self.commit = None

    def run(self):
        command = ['git', 'diff']
        if self.commit:
            command.append(self.commit)

        p = subprocess.Popen(command, stdout=subprocess.PIPE)
        while True:
            line = p.stdout.readline()
            if not line:
                break

            if line.startswith('diff ') or \
                    line.startswith('--- ') or \
                    line.startswith('+++ '):
                line = re.sub(' [ab]/', ' ', line)

            sys.stdout.write(line)
