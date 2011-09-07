"""Command to draw the revision tree of an RCS file."""

from cvsgit.cmd import Cmd
from cvsgit.rcs import RCSFile
from cvsgit.i18n import _

class rcstree(Cmd):
    __doc__ = _(
    """Dump all changes on the HEAD branch of an RCS file.

    Usage: %prog <rcsfile>

    Displays the changes on the HEAD branch of an RCS file for
    debugging purposes.
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
        print 'Head: %s' % rcsfile.head
        print 'Branch: %s' % rcsfile.branch
        print 'Revision trail:',
        for revision in rcsfile.revisions():
            print revision,
        print ''
        for change in rcsfile.changes():
            rcsfile._print_revision(change.revision)

if __name__ == '__main__':
    rcstree()
