from os.path import dirname, join
import subprocess
import unittest

from cvsgit.command.clone import Clone
from cvsgit.git import Git
from cvsgit.utils import Tempdir
from cvsgit.main import UnknownAuthorFullnames

class Test(unittest.TestCase):

    def setUp(self):
        self.tempdir = Tempdir(cwd=True)
        self.tempdir.__enter__()
        self.cvsdir = join(dirname(__file__), 'data', 'greek', 'tree')
        self.gitdir = 'tree'

    def tearDown(self):
        self.tempdir.__exit__(None, None, None)

    def cvs_clone(self, *args):
        """Clone CVS repo with default and additional arguments.
        """
        args += (self.cvsdir, self.gitdir)
        self.assertEquals(0, Clone().eval('--quiet', '--no-skip-latest', *args))

    def git_authors(self):
        """Return author name and email addresses from git.
        """
        return Git(self.gitdir).check_command('log', '--format=%an <%ae>',
                stdout=subprocess.PIPE)

    def test_clone_without_authors(self):
        """Clone without author mapping.
        """
        self.cvs_clone()
        self.assertEquals('uwe <uwe>', self.git_authors())

    def test_clone_with_authors_name(self):
        """Clone with author fullname mapping.
        """
        with open('authors', 'w') as authors:
            authors.write('uwe Some Dude\n')
        self.cvs_clone('--domain=example.com', '--authors=authors')
        self.assertEquals('Some Dude <uwe@example.com>', self.git_authors())

    def test_clone_with_authors_name_and_email(self):
        """Clone with author fullname and email mapping.
        """
        with open('authors', 'w') as authors:
            authors.write('uwe Some Dude <dude@example.com>\n')
        self.cvs_clone('--authors=authors')
        self.assertEquals('Some Dude <dude@example.com>', self.git_authors())

    def test_clone_with_unknown_auhtor(self):
        """Clone with unknown author and --stop-on-unknown-author.
        """
        with open('authors', 'w') as authors:
            authors.write('nobody Non-existent User\n')
        with self.assertRaises(UnknownAuthorFullnames):
            self.cvs_clone('--authors=authors', '--stop-on-unknown-author')
