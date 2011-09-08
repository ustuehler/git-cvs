import os
from os.path import dirname, join, isfile
from shutil import rmtree
import unittest

from cvsgit.command.clone import clone
from cvsgit.command.verify import verify
from cvsgit.utils import Tempdir

class Test(unittest.TestCase):

    def test_clone_bare(self):
        """Clone the greek tree into a bare repository.
        """
        with Tempdir(cwd=True) as tempdir:
            source = join(dirname(__file__), 'data', 'greek', 'tree')
            self.assertEquals(clone().eval('--quiet', '--bare', source), 0)
            self.assertTrue(isfile(join(tempdir, 'tree', 'config')))

    def test_clone_with_zombie_rcs_file(self):
        """Clone a repository that has a misplaced RCS file.

        This repository has a zombie copy of a file that was actually
        moved to Attic.
        """
        with Tempdir(cwd=True):
            source = join(dirname(__file__), 'data', 'zombie')
            self.assertEquals(0, clone().eval('--quiet', source))
            os.chdir('zombie')
            # FIXME: zombie repository fails verification
            #self.assertEquals(0, verify().eval())
