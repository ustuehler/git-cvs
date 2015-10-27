from StringIO import StringIO
from contextlib import contextmanager
from os import chdir, getcwd, mkdir
from os.path import dirname, join, isdir, isfile, exists
from string import split, strip
from subprocess import PIPE, Popen, call

import re
import shutil
import sys
import tempfile
import unittest

from cvsgit.command.init import init
from cvsgit.command.clone import Clone
from cvsgit.command.pull import pull
from cvsgit.command.verify import Verify
from cvsgit.git import Git

class TarFile(object):
    """Represents a tape archive file containing CVS repository files.

    CVS repositories are represented as tar files for the purpose of this test
    fixture because tar files include access and modification times, which
    allows an accurate simulation of the effects of running cvsync(1) between
    incremental imports.  It is possible to extract multiple tar files to the
    same target directory to overlay changes and keep the tar file sizes down.
    """

    def __init__(self, name):
        """Initialize access to a tar file named "data/pull/<name>.tar".
        """
        datadir = join(dirname(__file__), 'data', 'pull')
        self.tarfile = join(datadir, name) + '.tar'
        if not isfile(self.tarfile):
            raise RuntimeError('fixture data "%s" not found, %s does not exist'
                    % (name, self.tarfile))

    def extract(self, target):
        """Extract the tar file to the given target directory.
        
        If the target directory already exists, files in the CVS repository
        can be added or updated, but not removed.
        """
        if not isdir(target):
            mkdir(target)

        # Extract the fixture data into the target directory, applying access
        # and modification times of files contained in the archive.
        retcode = call(['tar', '-xpf', self.tarfile, '-C', target])
        if retcode != 0:
            raise RuntimeError("tar failed to extract %s, returned code %s" %
                    (self.tarfile, retcode))

class Test(unittest.TestCase):

    def setUp(self):
        """Clone the initial CVS repository into a temporary directory and
        change the working directory to the new work tree.
        """
        self.oldcwd = getcwd()
        self.tempdir = tempfile.mkdtemp()
        self.cvsroot = join(self.tempdir, 'cvs')
        self.worktree = join(self.tempdir, 'git')

        # Clone the initial CVS repository.
        TarFile('cvsroot').extract(self.cvsroot)
        TarFile('import').extract(self.cvsroot)
        chdir(self.tempdir)
        self.assertEquals(Clone().eval('--quiet', '--no-skip-latest',
            join(self.cvsroot, 'src'), self.worktree), 0)

        # Enter the work tree and make sure the clone was successful before
        # running the actual test case.
        chdir(self.worktree)
        self.assertEquals(Verify().eval(), 0)

        # Verify the intial Git state after cloning from "cvs import".
        self.git = Git(self.worktree)
        self.assertEquals(
            ['21d3c522acefc5d240848876968504d8ea85347f'],
            split(self.git.rev_list('HEAD')))

    def tearDown(self):
        """Return to the original working directory and remove the whole
        temporary directory.
        """
        # Ensure that the working copy is the same as cloning from CVS at
        # the end of each test fixture.
        self.assertEquals(Verify().eval(), 0)

        # Restore the original working directory.
        chdir(self.oldcwd)
        if isdir(self.tempdir):
            shutil.rmtree(self.tempdir)

    def test_initial_clone(self):
        """Pull without changes in CVS does nothing.

        Running "git cvs pull" right after an initial "git cvs clone"
        should not change the working copy in any way, even if an RCS
        file has an updated timestamp and is therefore parsed again.
        """
        touch_existing(join(self.cvsroot, 'src', 'file_a,v'))
        old_content = directory_listing(self.worktree)
        with redirect_stdout() as stdout:
            self.assertEquals(pull().eval('--no-skip-latest'), 0)
            self.assertEquals(stdout.getvalue(),
                re.sub('^\s*', '', """\
                Collecting RCS files: 1
                Parsing RCS files: done. (1/1)
                Processing changes: done. (0/0)
                """, 0, re.MULTILINE))
        new_content = directory_listing(self.worktree)
        self.assertEquals(old_content, new_content)

    def test_pull_new_file(self):
        """Pull a change that adds a new file.
        """
        TarFile('add-file_b').extract(self.cvsroot)
        self.assertEquals(isfile('file_a'), True)
        self.assertEquals(isfile('file_b'), False)
        with redirect_stdout() as stdout:
            self.assertEquals(pull().eval('--no-skip-latest'), 0)
            self.assertEquals(
                re.sub('^\s*', '', """\
                Collecting RCS files: 2
                Parsing RCS files: done. (1/1)
                Processing changes: done. (1/1)
                Importing changesets: done. (1/1)
                """, 0, re.MULTILINE),
                stdout.getvalue())
        self.assertEquals(isfile('file_b'), True)
        self.assertEquals(
            ['675ccc10b5cdca1ead0eec6020a16e3d51b8e548',
             '21d3c522acefc5d240848876968504d8ea85347f'],
            split(self.git.rev_list('HEAD')))

    def test_incomplete_commit(self):
        """Incomplete change sets are ignored by default.
        """
        TarFile('add-file_b').extract(self.cvsroot)
        TarFile('split-commit-part1').extract(self.cvsroot)
        with redirect_stdout() as stdout:
            self.assertEquals(pull().eval(), 0)
            self.assertEquals(
                ['Collecting RCS files: 2',
                 'Parsing RCS files: done. (2/2)',
                 'Processing changes: done. (3/3)',
                 'Retained changesets: 1',
                 'Importing changesets:  50% (1/2)',
                 'Importing changesets: done. (2/2)'],
                splitlines(stdout.getvalue()))
        self.assertEquals(
            ['24231f1cd29a5e1caaf9c0167283b8aa5955ea7f',
             '8d60be7401bafc50256ec624d1aa2ef3b63a2a41',
             '21d3c522acefc5d240848876968504d8ea85347f'],
            split(self.git.rev_list('HEAD')))

def splitlines(s):
    """Split string `s' into lines and trim whitespace.
    """
    return map(lambda l: strip(l), s.splitlines())

@contextmanager
def redirect_stdout():
    """Run a code block with sys.stdout redirected to a StringIO.
    Yields the StringIO object that captures the output.
    """
    oldout = sys.stdout
    try:
        out = StringIO()
        sys.stdout = out
        yield out
    finally:
        sys.stdout = oldout

def touch_existing(path):
    """Update the modification time of a directory entry.
    The entry must already exist or an error is raised.
    """
    if not exists(path):
        raise RuntimeError("missing directory entry: %s" % path)
    retcode = call(['touch', path])
    if retcode != 0:
        raise RuntimeError("touch command return code %s" % retcode)

def directory_listing(path):
    """Return a multi-line string listing the directory content.
    """
    ls = Popen(['ls', '-lR', path], stdout=PIPE)
    stdout, stderr = ls.communicate()
    retcode = ls.wait()
    if retcode == 0:
        return stdout
    else:
        raise RuntimeError("ls command returned code %s" % retcode)
