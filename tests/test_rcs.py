import unittest

from os.path import dirname, join

from cvsgit.rcs import RCSFile
from cvsgit.cvs import CVS # XXX: should not be needed here

class Test(unittest.TestCase):

    def testNoRevisionsOnTrunk(self):
        """RCS file without revisions on trunk yields no changes.

        This RCS file contains no revisions on the "trunk", i.e. the first
        trunk revision 1.1 is explicitly marked 'dead' but it is still a
        branchpoint for OpenBSD release branches in which the path exists.
        """
        f = RCSFile(join(dirname(__file__), 'data', 'patch-copyin_c,v'))
        for c in f.changes(): self.assertTrue(False)

    def testIncompleteRevisionTrail(self):
        """HEAD branch missing 1.3 and earlier ancestors

        The file sbin/isakmpd/Attic/pkcs.c,v in OpenBSD's src repostiory
        only contains revisions back to 1.4, but no earlier revisions.
        """
        f = RCSFile(join(dirname(__file__), 'data', 'pkcs.c,v'))
        for c in f.changes(): pass
        self.assertEqual('1.4', c.revision)

    def test_multiple_vendor_imports_and_no_revisions_on_trunk(self):
        """Respect the 'branch' field in the RCS header.

        This file was imported twice into the vendor branch but never
        modified in the HEAD branch.

        The RCS file is from OpenBSD CVS (src/usr.sbin/nsd/LICENSE).
        """
        f = RCSFile(join(dirname(__file__), 'data', 'nsd', 'LICENSE,v'))
        self.assertEqual(['1.1.1.1', '1.1.1.2'], list(f.revisions()))

    def test_keyword_substitution_edge_cases(self):
        """Test edge cases where RCS keyword expansion might fail.
        """
        blob = self.checkout('dot.commonutils,v', '1.1')
        s = '$Id: dot.commonutils,v 1.1 1995/10/18 08:37:54 deraadt Exp $'
        self.assertEqual(1651, blob.find(s))

        blob = self.checkout('res_query.c,v', '1.1')
        s = '$Id: res_query.c,v 1.1 1993/06/01 09:42:14 vixie Exp vixie "'
        self.assertEqual(3091, blob.find(s))

        blob = self.checkout('setjmp.h,v', '1.2')
        s = '$OpenBSD: setjmp.h,v 1.2 2001/03/29 18:52:19 drahn Exp $'
        self.assertEqual(3, blob.find(s))

        blob = self.checkout('test_cvs_import_01_seed1.txt,v,v', '1.1')
        s = '$Id: seed1.txt,v 1.1 2007/06/05 05:49:41 niallo Exp $'
        self.assertEqual(347, blob.find(s))

        f = RCSFile(join(dirname(__file__), 'data', 'pathnames.h,v'))
        self.assertEqual(list(f.revisions())[-1], '1.1.1.1')

    def checkout(self, filename, revision):
        # FIXME: RCS should do keyword substitution, not CVS!
        cvs = CVS(join(dirname(__file__), 'data', 'greek'), None)
        cvs.localid = 'OpenBSD'
        f = RCSFile(join(dirname(__file__), 'data', filename))
        c = f.change(revision)
        blob = f.blob(revision)
        return cvs.expand_keywords(blob, c, f, revision)
