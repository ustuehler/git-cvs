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
        # This RCS file contains no revisions on the "trunk", i.e. the
        # first trunk revision 1.1 is explicitly marked 'dead' but it
        # is still a branchpoint for OpenBSD release branches in which
        # the path exists.
        cvsroot = join(dirname(__file__), 'data', 'zombie')
        # TODO: Discard command output to keep the test output clean.
        self.assertEquals(clone().eval(cvsroot, self.tmpdir), 0)
        # TODO: Verify that the correct file was picked and the zombie
        # got ignored.

if __name__ == '__main__':
    unittest.main()
