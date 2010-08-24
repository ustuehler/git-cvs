"""Git interface module for CVSGit."""

import os.path
import subprocess

class Git(object):
    def __init__(self, wc_dir):
        # Turn wc_dir into an absolute path as soon as possible.  If
        # any other code uses os.chdir(), wc_dir is no longer valid.
        self.wc_dir = os.path.abspath(wc_dir)
        self.git_dir = os.path.join(wc_dir, '.git')

    def init(self):
        assert(self.call('init', self.wc_dir) == 0)

    def destroy(self):
        assert(subprocess.call(['rm', '-rf', self.wc_dir]) == 0)

    def call(self, command, *args):
        return subprocess.call(['git', command] + list(args))
