"""Git interface module for 'git-cvs'."""

import os
import time
import types
import shutil
import sys

from signal import signal, SIGINT, SIG_IGN
from subprocess import Popen, PIPE, check_call

from cvsgit.changeset import FILE_DELETED
from cvsgit.i18n import _

def stripnl(string):
    if string.endswith('\n'):
        return string[0:-1]
    else:
        raise RuntimeError("string doesn't end in newline: %s" % string)

class Git(object):
    """Represents a Git repository."""

    def __init__(self, directory=None, bare=None):
        """If 'directory' is None, the repository path will be
        determined by the GIT_DIR environment variable or derived from
        the current working directory."""

        if directory:
            if os.path.exists(directory):
                directory = os.path.abspath(directory)
            if not bare:
                if directory.endswith('.git'):
                    bare = True
                else:
                    directory = os.path.join(directory, '.git')
        else:
            bare = None

        self._is_bare_repository = bare
        self._git_dir = directory
        self._work_tree = None

    def get_git_dir(self):
        """Return the repository path.  When called for the first
        time, this method calls 'git rev-parse' to find the repository
        based on the GIT_DIR environment variable and current working
        directory.  If 'git rev-parse' fails then sys.exit() will be
        called with a non-zero return code.  If you want to catch this
        error then you must intercept the SystemExit exception.  The
        result is cached internally."""

        if self._git_dir is None:
            git = Popen(['git', 'rev-parse', '--git-dir'], stdout=PIPE)
            stdout = git.communicate()[0]
            if git.returncode != 0:
                sys.exit(git.returncode)
            self._git_dir = stripnl(stdout)
        return self._git_dir

    def get_work_tree(self):
        """Return the path to the working tree or False if the
        repository is bare and neither the GIT_WORK_TREE environment
        variable nor 'core.worktree' is set in the repository config.
        sys.exit() may be called if the repository path is invalid and
        you must handle the SystemExit exception if you wish to catch
        this error.  The result is cached internally."""

        if self._work_tree is None:
            if os.environ.has_key('GIT_WORK_TREE'):
                self._work_tree = os.environ['GIT_WORK_TREE']
            else:
                self._work_tree = self.config_get('core.worktree')
                if self._work_tree is None:
                    if self.is_bare_repository():
                        self._work_tree = False
                    else:
                        self._work_tree = os.path.dirname(self.git_dir)
        return self._work_tree

    git_dir = property(get_git_dir)
    work_tree = property(get_work_tree)

    def is_bare_repository(self):
        """Call 'git rev-parse' to see if the repository is bare or
        not.  If 'git rev-parse' returns a non-zero exit code, then
        sys.exit() will be called with the same exit code.  If you
        wish to catch this error you must intercept the SystemExit
        exception. The result is cached internally."""

        if self._is_bare_repository is None:
            git = Popen(['git', 'rev-parse', '--is-bare-repository'],
                        stdout=PIPE)
            stdout = git.communicate()[0]
            if git.returncode != 0:
                sys.exit(git.returncode)
            elif stripnl(stdout) == 'true':
                self._is_bare_repository = True
            else:
                self._is_bare_repository = False
        return self._is_bare_repository

    def init(self):
        """Initialize or reinitialize the repository."""

        if self._is_bare_repository:
            args = ['--bare']
        else:
            args = []

        env = os.environ.copy()
        if env.has_key('GIT_DIR'):
            del env['GIT_DIR']
        if env.has_key('GIT_WORK_TREE'):
            del env['GIT_WORK_TREE']

        directory_created = False
        try:
            if self._git_dir:
                if self._is_bare_repository:
                    directory = self._git_dir
                else:
                    directory = os.path.dirname(self._git_dir)
                if not os.path.isdir(directory):
                    os.mkdir(directory)
                    directory_created = True
            else:
                directory = os.getcwd()

            check_call(['git', 'init'] + args, env=env, cwd=directory)
        except:
            if directory_created:
                shutil.rmtree(directory)
            raise

    def _git_env(self):
        env = os.environ.copy()
        env['GIT_DIR'] = self.git_dir
        if env.has_key('GIT_WORK_TREE'):
            del env['GIT_WORK_TREE']
        return env

    def _git_call(self, args):
        check_call(['git'] + args, env=self._git_env())

    def checkout(self, *args):
        self._git_call(['checkout'] + list(args))

    def config_get(self, varname, default=None):
        pipe = Popen(['git', 'config', '--get', varname],
                     stdout=PIPE, env=self._git_env())
        stdout, stderr = pipe.communicate()
        if pipe.returncode != 0:
            return default
        else:
            return stripnl(stdout)

    def config_set(self, varname, value):
        self._git_call(['config', varname, value])

    def import_changesets(self, changesets, params={},
                          onprogress=None, total=None):

        class SignalIndicator():
            def __init__(self):
                self.count = 0
            def __call__(self, signalnum, frame):
                self.count += 1
            def isset(self):
                return self.count > 0

        marksfile = os.path.join(self.git_dir, 'cvsgit.marks')
        pipe = Popen(['git', 'fast-import',
                      '--export-marks=' + marksfile,
                      '--quiet'], stdin=PIPE, env=self._git_env(),
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

    def mark_changesets(self, changesets):
        filename = os.path.join(self.git_dir, 'cvsgit.marks')
        if not os.path.isfile(filename):
            return

        marks = {}
        f = file(filename, 'r')
        try:
            for line in f.readlines():
                mark, sha1 = line.rstrip().split()
                marks[int(mark[1:])] = sha1
        finally:
            f.close()

        for changeset in changesets:
            if marks.has_key(changeset.id):
                sha1 = marks[changeset.id]
                changeset.set_mark(sha1)

class GitFastImport(object):
    def __init__(self, pipe, branch='master', domain=None, verbose=False):
        self.pipe = pipe
        self.branch = branch
        self.domain = domain
        self.verbose = verbose
        self.last_changeset = None

    def add_changeset(self, changeset):
        name = self.author_name(changeset.author)
        email = self.author_email(changeset.author)
        when = self.raw_date(changeset.timestamp)

        if self.verbose:
            tstamp = time.strftime('%Y-%m-%d %H:%M:%S',
                time.gmtime(changeset.timestamp))
            print '[%d] %s %s' % (changeset.id, tstamp, name)
            teaser = changeset.log.splitlines()[0]
            if len(teaser) > 68:
                teaser = teaser[:68] + '...'
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
                print '\t%s %s %s' % (c.filestatus, c.filename, c.revision)
            if c.filestatus == FILE_DELETED:
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

    def raw_date(self, seconds):
        """Convert 'seconds' from seconds since the epoch to Git's
        native date format."""
        return '%s +0000' % (seconds)

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
