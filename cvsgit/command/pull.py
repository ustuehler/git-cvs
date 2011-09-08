"""Command to pull changes from CVS into the current branch."""

from cvsgit.main import Command, Conduit
from cvsgit.i18n import _

class pull(Command):
    __doc__ = _(
    """Update the CVS tracking branch and the current HEAD

    Usage: %prog [options]

    Does what the "fetch" command does and runs "git pull" afterwards
    to update the current branch.
    """)

    def initialize_options(self):
        self.add_option('--count', type='int', metavar='COUNT', help=\
            _("Stop importing after COUNT new commits."))
        self.add_option('--quiet', action='store_true', help=\
            _("Only report error and warning messages."))
        self.add_option('--verbose', action='store_true', help=\
            _("Display each changeset as it is imported."))

    def finalize_options(self):
        if len(self.args) > 0:
            self.usage_error(_('too many arguments'))

    def run(self):
        conduit = Conduit()
        conduit.pull(count=self.options.count,
                     quiet=self.options.quiet,
                     verbose=self.options.verbose)

if __name__ == '__main__':
    pull()
