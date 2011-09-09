import os
from os.path import dirname, join, isfile
from shutil import rmtree
import unittest

from cvsgit.command.init import init
from cvsgit.command.clone import clone
from cvsgit.command.pull import pull
from cvsgit.command.verify import verify
from cvsgit.git import Git
from cvsgit.utils import Tempdir

class Test(unittest.TestCase):

    def test_clone(self):
        """Clone the greek tree and verify it.
        """
        with Tempdir(cwd=True) as tempdir:
            source = join(dirname(__file__), 'data', 'greek', 'tree')
            self.assertEquals(clone().eval('--quiet', source), 0)
            os.chdir('tree')
            self.assertEquals(0, verify().eval())

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

    def test_clone_partial_alternative(self):
        """Calling "clone --partial" several times is the same as
        "clone --partial" followed by "fetch".
        """
        head1 = None
        with Tempdir(cwd=True) as tempdir:
            source = join(dirname(__file__), 'data', 'greek', 'tree')
            self.assertEquals(0, init().eval('--quiet', source))
            self.assertEquals(0, clone().eval('--quiet', '--partial', source, '.'))
            head1 = Git().rev_parse('HEAD')

        head2 = None
        with Tempdir(cwd=True) as tempdir:
            source = join(dirname(__file__), 'data', 'greek', 'tree')
            self.assertEquals(0, init().eval('--quiet', source))
            self.assertEquals(0, pull().eval())
            head2 = Git().rev_parse('HEAD')

        self.assertEqual(head1, head2)
