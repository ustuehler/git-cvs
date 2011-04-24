"""Command to fetch unfetched revisions from the tracked CVS
repository."""

from cvsgit.app import GitCVS, Command
from cvsgit.i18n import _

class fetch(Command):
    __doc__ = _(
    """Fetch unfetched revisions from the CVS repository.

    Usage: %prog [options]

    Fetches unfetched revisions from the CVS repository we are
    tracking.
    """)

    def initialize_options(self):
        pass

    def finalize_options(self):
        if len(self.args) > 0:
            self.usage_error(_('too many arguments'))

    def run(self):
        gitcvs = GitCVS()
        gitcvs.fetch()

if __name__ == '__main__':
    fetch()
