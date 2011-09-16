from os.path import dirname, join

import unittest

from cvsgit.cvs import CVS
from cvsgit.changeset import Change

class Test(unittest.TestCase):

    def test_rcsfilename(self):
        """Find the RCS file for a working copy path.
        """
        cvs = CVS(join(dirname(__file__), 'data', 'zombie'), None)
        c = Change(timestamp='',
                   author='',
                   log='',
                   filestatus='',
                   filename='patches/patch-Makefile',
                   revision='',
                   state='',
                   mode='')
        expected = join(cvs.root, 'patches/Attic/patch-Makefile,v')
        actual = cvs.rcsfilename(c)
        self.assertEqual(expected, actual)
