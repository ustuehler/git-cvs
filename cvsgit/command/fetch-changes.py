"""Command to fetch changes from the CVS repository."""

import re
import subprocess
from subprocess import PIPE
import sys

from cvsgit.cvs import split_cvs_source
from cvsgit.i18n import _
from cvsgit.main import Command, Conduit
from cvsgit.utils import Tempdir, stripnl
from cvsgit.term import NoProgress, Progress

class FetchChanges(Command):
    __doc__ = _(
    """Fetch changes from CVS

    Usage: %prog

    Fetches unseen changes from the CVS repository and stores them
    locally for changeset generation at a later point in time.
    """)

    def initialize_options(self):
        self.add_quiet_option()

    def finalize_options(self):
        if len(self.args) > 0:
            self.usage_error(_('too many arguments'))

        if self.options.quiet:
            self.progress = NoProgress()
        else:
            self.progress = Progress()

    def run(self):
        conduit = Conduit()
        cvs = conduit.cvs
        cvs.fetch_changes(progress=self.progress)
