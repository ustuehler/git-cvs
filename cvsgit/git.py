"""Git interface module for CVSGit."""

import os
import time
import types

from subprocess import Popen, PIPE, check_call

from cvsgit.changeset import FILE_DELETED
from cvsgit.i18n import _

class Git(object):
    def __init__(self, wc_dir, domain='local', branch='master'):
        # Turn wc_dir into an absolute path as soon as possible.  If
        # any other code uses os.chdir(), wc_dir is no longer valid.
        self.wc_dir = os.path.abspath(wc_dir)
        self.git_dir = os.path.join(wc_dir, '.git')
        self.domain = domain
        self.branch = branch

    def init(self):
        check_call(['git', 'init', self.wc_dir])

    def destroy(self):
        check_call(['rm', '-rf', self.wc_dir])

    def config_get(self, varname, default=None):
        pipe = Popen(['git', 'config', '--get', varname],
                     stdout=PIPE, cwd=self.wc_dir)
        stdout, stderr = pipe.communicate()
        if pipe.returncode != 0:
            return default
        else:
            return stdout

    def config_set(self, varname, value):
        check_call(['git', 'config', varname, value], cwd=self.wc_dir)

    def import_changeset(self, changeset, **kwargs):
        pipe = Popen(['git', 'fast-import',
                      '--export-marks=.git/cvsgit.marks',
                      '--quiet'],
                     stdin=PIPE, cwd=self.wc_dir)

        fi = GitFastImport(pipe, **kwargs)
        try:
            fi.add_changeset(changeset)
        finally:
            fi.close()
        if fi.returncode != 0:
            raise RuntimeError, _('git fast-import failed')

        f = file(os.path.join(self.git_dir, 'cvsgit.marks'), 'r')
        try:
            for line in f.readlines():
                mark, sha1 = line.rstrip().split()
                if mark == ':' + str(changeset.id):
                    changeset.mark = sha1
        finally:
            f.close()

class GitFastImport(object):
    def __init__(self, pipe, branch='master',
                 domain=None, tz=None):
        self.pipe = pipe
        self.branch = branch
        self.domain = domain
        self.tz = tz

    def add_changeset(self, changeset):
        name = self.author_name(changeset.author)
        email = self.author_email(changeset.author)
        when = self.raw_date(changeset.timestamp)
        when_s = time.strftime('%c', time.localtime(changeset.timestamp))

        print 'committer %s <%s> %s' % (name, email, when_s)
        self.write('commit refs/heads/%s\n' % self.branch)
        self.write('mark :%s\n' % changeset.id)
        self.write('committer %s <%s> %s\n' % (name, email, when))
        self.data(changeset.log.encode('utf-8'))
        if changeset.id != 1:
            self.write('from refs/heads/%s^0\n' % self.branch)

        for c in changeset.changes:
            print '\t%s %s %s' % (c.state, c.filename, c.revision)
            if c.state == FILE_DELETED:
                self.write('D %s\n' % c.filename)
            else:
                self.write('M 644 inline %s\n' % c.filename)
                self.data(changeset.blob(c))

    def close(self):
        self.pipe.stdin.close()
        self.returncode = self.pipe.wait()

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
        if self.domain:
            return '%s@%s' % (author, self.domain)
        else:
            return author

    def data(self, data):
        "'data' must be a raw binary string of the str() type."
        assert(type(data) == types.StringType)
        self.write('data %d\n' % len(data))
        self.write(data)
        self.write('\n')

    def write(self, data):
        self.pipe.stdin.write(data)
