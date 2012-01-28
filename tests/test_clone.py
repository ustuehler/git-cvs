import os
from os.path import dirname, join, isfile
from shutil import rmtree
import unittest

from cvsgit.command.init import init
from cvsgit.command.clone import Clone
from cvsgit.command.pull import pull
from cvsgit.command.verify import Verify
from cvsgit.git import Git
from cvsgit.utils import Tempdir

class Test(unittest.TestCase):

    def test_clone(self):
        """Clone the greek tree and verify it.
        """
        with Tempdir(cwd=True) as tempdir:
            source = join(dirname(__file__), 'data', 'greek', 'tree')
            self.assertEquals(Clone().eval('--quiet', source), 0)
            os.chdir('tree')
            self.assertEquals(0, Verify().eval())

            # A/mu inherits the executable bits from the RCS file.
            rcs_mode = os.stat(join(source, 'A/mu,v')).st_mode
            wc_mode = os.stat('A/mu').st_mode
            self.assertTrue((rcs_mode & 0111) != 0)
            self.assertEquals(rcs_mode, wc_mode)

    def test_clone_bare(self):
        """Clone the greek tree into a bare repository.
        """
        with Tempdir(cwd=True) as tempdir:
            source = join(dirname(__file__), 'data', 'greek', 'tree')
            self.assertEquals(Clone().eval('--quiet', '--bare', source), 0)
            self.assertTrue(isfile(join(tempdir, 'tree', 'config')))

    def test_clone_with_zombie_rcs_file(self):
        """Clone a repository that has a misplaced RCS file.

        This repository has a zombie copy of a file that was actually
        moved to Attic.
        """
        with Tempdir(cwd=True):
            source = join(dirname(__file__), 'data', 'zombie')
            self.assertEquals(0, Clone().eval('--quiet', source))
            os.chdir('zombie')
            # FIXME: zombie repository fails verification
            #self.assertEquals(0, Verify().eval())

    def test_clone_partial_alternative(self):
        """Calling "pull --limit=<limit>" several times is basically
        the same as cloning everything (given that it's done enough
        times or that <limit> is high enough.)
        """
        head1 = None
        with Tempdir(cwd=True) as tempdir:
            source = join(dirname(__file__), 'data', 'zombie')
            self.assertEquals(0, Clone().eval('--quiet', source))
            os.chdir('zombie')
            head1 = Git().rev_parse('HEAD')

        head2 = None
        with Tempdir(cwd=True) as tempdir:
            source = join(dirname(__file__), 'data', 'zombie')
            self.assertEquals(0, init().eval('--quiet', source))
            self.assertEquals(0, pull().eval('--quiet', '--limit=1'))
            self.assertNotEqual(head1, Git().rev_parse('HEAD'))
            self.assertEquals(0, pull().eval('--quiet', '--limit=2'))
            self.assertNotEqual(head1, Git().rev_parse('HEAD'))
            self.assertEquals(0, pull().eval('--quiet', '--limit=3'))
            self.assertEqual(head1, Git().rev_parse('HEAD'))

    def test_git_clone_from_cvs_clone(self):
        """Cloning a new Git repo from a bare CVS tracking repo.
        """
        head1 = None
        with Tempdir(cwd=True) as tempdir:
            source = join(dirname(__file__), 'data', 'zombie')
            self.assertEquals(0, Clone().eval('--quiet', source, 'test.git'))
            Git().check_command('clone', '--quiet', 'test.git')
            self.assertEquals(Git('test.git').rev_parse('HEAD'),
                              Git('test').rev_parse('HEAD'))
            self.assertEquals('refs/heads/master',
                              Git('test').symbolic_ref('HEAD'))
