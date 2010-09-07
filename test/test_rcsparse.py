import unittest
from rcsparse import rcsfile
from os.path import dirname, join

REV_NUMBER = 0
REV_STATE = 3

class Test(unittest.TestCase):

    def test_rcsfile(self):
        f = rcsfile(join(dirname(__file__), 'data', 'patch-copyin_c,v'))
        self.assertEquals(f.head, '1.1')
        self.assertEquals(f.revs[f.head][REV_NUMBER], '1.1')
        self.assertEquals(f.revs[f.head][REV_STATE], 'dead')

if __name__ == '__main__':
    unittest.main()
