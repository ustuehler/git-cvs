import unittest
from cvsgit.rcs import RCSFile
from os.path import dirname, join

class Test(unittest.TestCase):

    def testNoRevisionsOnTrunk(self):
        # This RCS file contains no revisions on the "trunk", i.e. the
        # first trunk revision 1.1 is explicitly marked 'dead' but it
        # is still a branchpoint for OpenBSD release branches in which
        # the path exists.
        f = RCSFile(join(dirname(__file__), 'data', 'patch-copyin_c,v'))
        for c in f.changes(): self.assertTrue(False)
