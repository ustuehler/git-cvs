"""Test the cvsgit.git module

This test suite requires at least Python 2.5 with 'with_statement'
feature enabled or Python 2.6.
"""

import os
import shutil
import tempfile
import unittest

from os.path import dirname, join, isdir, isfile, exists

from cvsgit.git import Git

class Tempdir(object):
    """Manage a tempoarary directory

    >>> with Tempdir() as tempdir:
    ...   # work inside tempdir
    """

    def __init__(self, cwd=False):
        """Initialize a Tempdir context

        If 'cwd' is True, make the temporary directory the current
        working directory when the context is entered and restore
        the previous working directory when the context is exited.
        """
        self.cwd = cwd

    def __enter__(self):
        self.tempdir = tempfile.mkdtemp()
        if self.cwd:
            self.pwd = os.getcwd()
            os.chdir(self.tempdir)
        return self.tempdir

    def __exit__(self, exception_type, value, traceback):
        if self.cwd:
            os.chdir(self.pwd)
        if isdir(self.tempdir):
            shutil.rmtree(self.tempdir)
        return False

class Environ(object):
    """Environment variable context

    >>> with Environ(PATH='/bin:/usr/bin'):
    ...   # do something
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        self.oldenv = os.environ.copy()
        for k in self.kwargs.keys():
            v = self.kwargs[k]
            if v == None:
                if os.environ.has_key(k):
                    del os.environ[k]
            else:
                os.environ[k] = v
        return os.environ

    def __exit__(self, exception_type, value, traceback):
        os.environ = self.oldenv
        return False

class Test(unittest.TestCase):

    def test_init_working_directory(self):
        """Initialize a Git repository in the working directory.
        """
        with Tempdir(cwd=True) as tempdir:
            git = Git()
            self.assertEquals(tempdir, git.git_work_tree)
            self.assertEquals(join(tempdir, '.git'), git.git_dir)

            git.init(quiet=True)
            self.assertEquals(tempdir, git.git_work_tree)
            self.assertEquals(join(tempdir, '.git'), git.git_dir)
            self.assertTrue(isdir(join(tempdir, '.git')))

            git.destroy()
            self.assertFalse(isdir(tempdir))

    def test_init_bare_working_directory(self):
        """Initialize a bare repository in the working directory.
        """
        with Tempdir(cwd=True) as tempdir:
            git = Git()
            self.assertEquals(tempdir, git.git_work_tree)
            self.assertEquals(join(tempdir, '.git'), git.git_dir)

            git.init(bare=True, quiet=True)
            self.assertEquals(None, git.git_work_tree)
            self.assertEquals(tempdir, git.git_dir)
            self.assertFalse(isdir(join(tempdir, '.git')))
            self.assertTrue(isfile(join(tempdir, 'config')))
            self.assertTrue(isdir(join(tempdir, 'objects')))

            git.destroy()
            self.assertFalse(isdir(tempdir))

    def test_init_specified_directory(self):
        """Initialize a Git repository in another directory.
        """
        with Tempdir(cwd=True) as tempdir:
            directory = join(tempdir, 'repo')
            git = Git(directory)
            git.init(quiet=True)
            self.assertEquals(directory, git.git_work_tree)
            self.assertEquals(join(directory, '.git'), git.git_dir)
            self.assertTrue(isdir(join(directory, '.git')))

            git.destroy()
            self.assertFalse(isdir(directory))
            self.assertTrue(isdir(tempdir))

    def test_config_set_and_get(self):
        """Set and get per-repository config values.
        """
        with Tempdir(cwd=True) as tempdir:
            git = Git()
            self.assertEquals(None, git.config_get('foo.bar'))
            git.init(quiet=True)
            git.config_set('foo.bar', 'baz')
            self.assertEquals('baz', git.config_get('foo.bar'))
