"""Command to fetch unfetched revisions from the tracked CVS
repository."""

from cvsgit.main import Command, Conduit
from cvsgit.i18n import _

class fetch(Command):
    __doc__ = _(
    """Fetch unfetched revisions from CVS.

    Usage: %prog [options]

    Fetches unfetched changes from the CVS repository we are tracking,
    merges them into related changesets and imports them into Git.
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
        conduit.fetch(limit=self.options.limit,
                      quiet=self.options.quiet,
                      verbose=self.options.verbose,
                      authors=self.options.authors,
                      stop_on_unknown_author=\
                          self.options.stop_on_unknown_author)

if __name__ == '__main__':
    fetch()
