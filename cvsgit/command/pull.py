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
        self.add_option('--limit', type='int', metavar='COUNT', help=\
            _("Stop importing after COUNT new commits."))
        self.add_option('--quiet', action='store_true', help=\
            _("Only report error and warning messages."))
        self.add_option('--verbose', action='store_true', help=\
            _("Display each changeset as it is imported."))
        self.add_authors_option()
        self.add_stop_on_unknown_author_option()

    def finalize_options(self):
        if len(self.args) > 0:
            self.usage_error(_('too many arguments'))

        self.finalize_authors_option()

    def run(self):
        conduit = Conduit()
        conduit.pull(limit=self.options.limit,
                     quiet=self.options.quiet,
                     verbose=self.options.verbose,
                     authors=self.options.authors,
                     stop_on_unknown_author=\
                         self.options.stop_on_unknown_author)

if __name__ == '__main__':
    pull()
