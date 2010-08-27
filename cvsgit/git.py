"""Git interface module for CVSGit."""

import os
import time
import types

from signal import signal, SIGINT, SIG_IGN
from subprocess import Popen, PIPE, check_call

from cvsgit.changeset import FILE_DELETED
from cvsgit.i18n import _

class Git(object):
    def __init__(self, wc_dir, domain='local', branch='master'):
        # Turn wc_dir into an absolute path as soon as possible.  If
        # any other code uses os.chdir(), wc_dir is no longer valid.
        self.wc_dir = os.path.abspath(wc_dir)
        if self.wc_dir.endswith('.git'):
            self.git_dir = self.wc_dir
        else:
            self.git_dir = os.path.join(wc_dir, '.git')
        self.domain = domain
        self.branch = branch

    def init(self):
        # Old version of 'git init' does not accept a directory argument.
        check_call(['mkdir', '-p', self.wc_dir])
        if self.wc_dir == self.git_dir:
            check_call(['git', 'init', '--bare'], cwd=self.wc_dir)
        else:
            check_call(['git', 'init'], cwd=self.wc_dir)

    def destroy(self):
        check_call(['rm', '-rf', self.wc_dir])

    def config_get(self, varname, default=None):
        pipe = Popen(['git', 'config', '--get', varname],
                     stdout=PIPE, cwd=self.git_dir)
        stdout, stderr = pipe.communicate()
        if pipe.returncode != 0:
            return default
        else:
            return stdout

    def config_set(self, varname, value):
        check_call(['git', 'config', varname, value], cwd=self.git_dir)

    def import_changesets(self, changesets, params={},
                          onprogress=None, total=None):

        class SignalIndicator():
            def __init__(self):
                self.count = 0
            def __call__(self, signalnum, frame):
                self.count += 1
            def isset(self):
                return self.count > 0

        pipe = Popen(['git', 'fast-import', '--export-marks=cvsgit.marks',
                      '--quiet'], stdin=PIPE, cwd=self.git_dir,
                      preexec_fn=lambda: signal(SIGINT, SIG_IGN))

        sigint_flag = SignalIndicator()
	old_sigaction = signal(SIGINT, sigint_flag)

        fi = GitFastImport(pipe, **params)
        changesets_seen = []
        try:
            for changeset in changesets:
                if onprogress and total and not params.get('verbose'):
                    onprogress(len(changesets_seen), total)

                changesets_seen.append(changeset)
                fi.add_changeset(changeset)

                if sigint_flag.isset():
                    raise KeyboardInterrupt()
        finally:
            try:
                fi.close()
            finally:
                self.mark_changesets(changesets_seen)
                signal(SIGINT, old_sigaction)

        if fi.returncode != 0:
            raise RuntimeError, _('git fast-import failed')

    def mark_changesets(self, imported_changesets):
        filename = os.path.join(self.git_dir, 'cvsgit.marks')
        if not os.path.isfile(filename):
            return
        f = file(filename, 'r')
        try:
            marks = {}
            for line in f.readlines():
                mark, sha1 = line.rstrip().split()
                marks[int(mark[1:])] = sha1
            for changeset in imported_changesets:
                if marks.has_key(changeset.id):
                    changeset.set_mark(marks[changeset.id])
        finally:
            f.close()

class GitFastImport(object):
    def __init__(self, pipe, branch='master', domain=None, tz=None,
                 verbose=False):
        self.pipe = pipe
        self.branch = branch
        self.domain = domain
        self.tz = tz
        self.verbose = verbose
        self.last_changeset = None

    def add_changeset(self, changeset):
        name = self.author_name(changeset.author)
        email = self.author_email(changeset.author)
        when = self.raw_date(changeset.timestamp)
        when_s = time.strftime('%c', time.localtime(changeset.timestamp))

        if self.verbose:
            teaser = changeset.log.splitlines()[0]
            if len(teaser) > 68:
                teaser = teaser[:68] + '...'
            print '[%d] %s %s' % (changeset.id, name, when_s)
            print '\t%s' % teaser.encode('ascii', 'replace')

        self.write('commit refs/heads/%s\n' % self.branch)
        self.write('mark :%s\n' % changeset.id)
        self.write('committer %s <%s> %s\n' % (name, email, when))
        self.data(changeset.log.encode('utf-8'))

        if changeset.id != 1:
            # FIXME: this is a hack; find out if the branch exists
            if self.last_changeset is None:
                self.write('from refs/heads/%s^0\n' % self.branch)
            else:
                self.write('from :%s\n' % self.last_changeset.id)
        self.last_changeset = changeset

        for c in changeset.changes:
            if self.verbose:
                print '\t%s %s %s' % (c.state, c.filename, c.revision)
            if c.state == FILE_DELETED:
                self.write('D %s\n' % c.filename)
            else:
                self.write('M 644 inline %s\n' % c.filename)
                self.data(changeset.blob(c))

    def close(self):
        try:
            self.pipe.stdin.close()
            self.pipe.wait()
        except:
            pass
        self.returncode = self.pipe.returncode

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
