"""Command to dump the full state of the source tree at a certain
point in time."""

import re
import subprocess
from subprocess import PIPE
import sys

from cvsgit.cvs import split_cvs_source
from cvsgit.i18n import _
from cvsgit.main import Command, Conduit
from cvsgit.utils import Tempdir, stripnl

class dump_tree(Command):
    __doc__ = _(
    """Dump the source tree state at a certain date

    Usage: %prog <date>

    Computes and dumps the state of the source tree as it was at the
    given <date>.
    """)

    def initialize_options(self):
        pass

    def finalize_options(self):
        if len(self.args) > 0:
            self.usage_error(_('too many arguments'))

    def run(self):
        conduit = Conduit()
        cvs = conduit.cvs
        for changeset in cvs.changesets():
            print changeset

if __name__ == '__main__':
    dump_tree()
