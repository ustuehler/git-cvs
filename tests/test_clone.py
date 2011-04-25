import unittest
from cvsgit.command.clone import clone
from os.path import dirname, join, exists
from shutil import rmtree

class Test(unittest.TestCase):

    def setUp(self):
        self.tmpdir = join(dirname(__file__), 'tmp')

    def tearDown(self):
        if exists(self.tmpdir):
            rmtree(self.tmpdir)

    def testZombieDetection(self):
        # This repository has a zombie copy of a file that was actually
        # moved to Attic.
        cvsroot = join(dirname(__file__), 'data', 'zombie')
        # TODO: Discard command output to keep the test output clean.
        self.assertEquals(clone().eval('--quiet-git', cvsroot, self.tmpdir), 0)
        # TODO: Verify that the correct file was picked and the zombie
        # got ignored.

if __name__ == '__main__':
    unittest.main()
