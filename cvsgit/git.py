"""Git interface module for CVSGit."""

import os
import subprocess
import time
import types

from subprocess import Popen, PIPE
from cvsgit.db import FILE_ADDED, FILE_MODIFIED, FILE_DELETED
from cvsgit.i18n import _

class GitFastImport(object):
    def __init__(self, pipe, branch='master', domain='local', tz=None):
        self.pipe = pipe
        self.branch = branch
        self.domain = domain
        self.tz = tz

    def offutc(self, seconds):
        oldtz = os.environ.get('TZ')
        try:
            if self.tz:
                os.environ['TZ'] = self.tz
                time.tzset()

            # Enable if RCS returns the timestamp in local time, not UTC.
            #seconds -= time.timezone

            if time.localtime(seconds)[8] == 1: # is DST?
                offutc_sec = time.altzone
            else:
                offutc_sec = time.timezone

            offutc = offutc_sec / 60 / 60 * 100
            offutc += offutc_sec / 60 % 60
            return offutc

        finally:
            if oldtz:
                os.environ['TZ'] = oldtz
            elif self.tz:
                del os.environ['TZ']
            time.tzset()

    def raw_date(self, seconds):
        """Convert 'seconds' from source time zone to Git's native
        date format."""
        return '%s %+.4d' % (seconds, self.offutc(seconds))

    def author_name(self, author):
        return author

    def author_email(self, author):
        return '%s@%s' % (author, self.domain)

    def commit(self, cvs, commit):
        name = self.author_name(commit.author)
        email = self.author_email(commit.author)
        when = self.raw_date(commit.timestamp)
        when_s = time.strftime('%c', time.localtime(commit.timestamp))

        print 'committer %s <%s> %s' % (name, email, when_s)
        self.write('commit refs/heads/%s\n' % self.branch)
        self.write('committer %s <%s> %s\n' % (name, email, when))
        self.data(commit.log.encode('utf-8'))
        # TODO: maybe we need this for incremental updates?
        #self.write('from refs/heads/%s^0\n' % self.branch)

        for c in commit.changes:
            print '\t%s %s %s' % (c.state, c.file, c.revision)
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
        self.write('\n')

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

    def fast_import(self, **kwargs):
        env = os.environ.copy()
        env['GIT_DIR'] = self.git_dir
        pipe = Popen(['git', 'fast-import', '--quiet'], stdin=PIPE, env=env)
        return GitFastImport(pipe, **kwargs)
