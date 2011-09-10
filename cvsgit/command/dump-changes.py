"""Command to dump changes fetched from CVS."""

import re
import subprocess
from subprocess import PIPE
import sys

from cvsgit.cvs import split_cvs_source
from cvsgit.i18n import _
from cvsgit.main import Command, Conduit
from cvsgit.utils import Tempdir, stripnl
from cvsgit.term import NoProgress, Progress

class DumpChanges(Command):
    __doc__ = _(
    """Dump changes fetched from CVS

    Usage: %prog

    Dumps all previously fetched changes from the CVS repository.
    """)

    def initialize_options(self):
        pass

    def finalize_options(self):
        if len(self.args) > 0:
            self.usage_error(_('too many arguments'))

    def run(self):
        cvs = Conduit().cvs
        for change in cvs.changes():
            print change
