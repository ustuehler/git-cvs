"""Command to draw the revision tree of an RCS file."""

from cvsgit.cmd import Cmd
from cvsgit.rcs import RCSFile
from cvsgit.i18n import _

class rcstree(Cmd):
    __doc__ = _(
    """Draw the revision tree of an RCS file.

    Usage: %prog <rcsfile>

    Displays the revisions of an RCS file as a tree for debugging
    purposes.
    """)

    def initialize_options(self):
        self.rcsfile = None

    def finalize_options(self):
        if len(self.args) < 1:
            self.usage_error(_('missing RCS file argument'))
        elif len(self.args) == 1:
            self.rcsfile = self.args[0]
        else:
            self.usage_error(_('too many arguments'))

    def run(self):
        rcsfile = RCSFile(self.rcsfile)
        for revision in rcsfile._revisions():
            rcsfile._print_revision(revision)

if __name__ == '__main__':
    rcstree()
