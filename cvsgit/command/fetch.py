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
        pass

    def finalize_options(self):
        if len(self.args) > 0:
            self.usage_error(_('too many arguments'))

    def run(self):
        conduit = Conduit()
        conduit.fetch()

if __name__ == '__main__':
    fetch()
