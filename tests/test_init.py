"""Test conduit initialization

This test suite requires at least Python 2.5 with 'with_statement'
feature enabled or Python 2.6.
"""

import os
import shutil
import tempfile
import unittest

from os.path import dirname, join, isdir, isfile, exists

from cvsgit.command.init import init
from cvsgit.git import Git
from cvsgit.utils import Tempdir

class Test(unittest.TestCase):

    def test_init_command(self):
        """Initialize the conduit in the working directory.
        """
        with Tempdir(cwd=True) as tempdir:
            repository = join(dirname(__file__), 'data', 'greek')
            self.assertEquals(0, init().eval('--quiet', repository))
            self.assertEquals(repository, Git().config_get('cvs.source'))
