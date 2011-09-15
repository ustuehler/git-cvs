"""Command to draw the revision tree of an RCS file."""

import os

from cvsgit.main import Command
from cvsgit.rcs import RCSFile
from cvsgit.i18n import _

# FIXME: RCS should expand keywords, not CVS
from cvsgit.cvs import CVS

class Rcsdump(Command):
    __doc__ = _(
    """Dump all changes on the HEAD branch of an RCS file.

    Usage: %prog [options] <rcsfile>

    Displays the changes on the HEAD branch of an RCS file for
    debugging purposes.
    """)

    def initialize_options(self):
        self.add_option('--checkout', metavar='REVISION', help=\
            _("Dump the content of the specified REVISION."))

    def finalize_options(self):
        if len(self.args) < 1:
            self.usage_error(_('missing RCS file argument'))
        elif len(self.args) == 1:
            self.rcsfile = self.args[0]
        else:
            self.usage_error(_('too many arguments'))

    def run(self):
        rcsfile = RCSFile(self.rcsfile)

        if self.options.checkout:
            return self.checkout(rcsfile, self.options.checkout)

        print 'Head: %s' % rcsfile.head
        print 'Branch: %s' % rcsfile.branch
        print 'Revision trail:',
        for revision in rcsfile.revisions():
            print revision,
        print ''
        for change in rcsfile.changes():
            rcsfile._print_revision(change.revision)

    def checkout(self, rcsfile, revision):
        change = rcsfile.change(revision)
        size = os.stat(self.rcsfile).st_size
        blob = rcsfile.blob(revision, size_hint=size)
        cvs = CVS(os.path.join(os.path.dirname(rcsfile.filename)), None)
        print cvs.expand_keywords(blob, change, rcsfile, revision)
