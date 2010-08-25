"""Git interface module for CVSGit."""

import os
import subprocess
import types

from subprocess import Popen, PIPE
from cvsgit.db import FILE_ADDED, FILE_MODIFIED, FILE_DELETED
from cvsgit.i18n import _

class GitFastImport(object):
    def __init__(self, git, pipe):
        self.git = git
        self.pipe = pipe

    def commit(self, cvs, commit):
        name = self.git.author_name(commit.author)
        email = self.git.author_email(commit.author)
        when = 'now' # FIXME: use commit.timestamp

        self.write('commit refs/heads/%s\n' % self.git.branch)
        self.write('committer %s <%s> %s\n' % (name, email, when))

        self.data(commit.log.encode('utf-8'))

        # TODO: maybe we need this for incremental updates?
        #self.write('from refs/heads/%s^0\n' % self.git.branch)

        for c in commit.changes:
            if c.state == FILE_DELETED:
                self.write('D %s\n' % c.file)
            else:
                self.write('M 644 inline %s\n' % c.file)
                self.data(cvs.blob(c.file, c.revision))

    def data(self, data):
        "'data' must be a raw binary string of the str() type."
        assert(type(data) == types.StringType)
        self.write('data %d\n' % len(data))
        self.write(data)

    def write(self, data):
        self.pipe.stdin.write(data)

    def close(self):
        self.pipe.stdin.close()
        if self.pipe.wait() != 0:
            raise RuntimeError, _('git fast-import failed')

class Git(object):
    def __init__(self, wc_dir, domain='local', branch='master'):
        # Turn wc_dir into an absolute path as soon as possible.  If
        # any other code uses os.chdir(), wc_dir is no longer valid.
        self.wc_dir = os.path.abspath(wc_dir)
        self.git_dir = os.path.join(wc_dir, '.git')
        self.domain = domain
        self.branch = branch

    def init(self):
        assert(self.call('init', self.wc_dir) == 0)

    def destroy(self):
        assert(subprocess.call(['rm', '-rf', self.wc_dir]) == 0)

    def call(self, command, *args):
        return subprocess.call(['git', command] + list(args))

    def fast_import(self):
        env = os.environ.copy()
        env['GIT_DIR'] = self.git_dir
        pipe = Popen(['git', 'fast-import', '--quiet',
                      '--date-format=now'], # FIXME
                     stdin=PIPE, env=env)
        return GitFastImport(self, pipe)

    def author_name(self, author):
        return author

    def author_email(self, author):
        return '%s@%s' % (author, self.domain)
