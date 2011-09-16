"""Git interface module for 'git-cvs'."""

import os
import time
import types
import shutil
import sys

from signal import signal, SIGHUP, SIGINT, SIGTERM, SIG_IGN
from subprocess import Popen, PIPE

from cvsgit.changeset import FILE_DELETED
from cvsgit.i18n import _
from cvsgit.error import Error
from cvsgit.utils import stripnl
from cvsgit.term import NoProgress

# I don't know how GIT_DIR and GIT_WORK_TREE and GIT_OBJECT_DIRECTORY
# and all the rest could affect us here, so I'll just discard them all
# for now.
def safe_environ():
    env = os.environ.copy()
    for k in env.keys():
        if k.startswith('GIT_'):
            del env[k]

class GitError(Error):
    """Base exception for errors in the cvsgit.git module"""
    pass

class GitCommandError(GitError):
    """Failure to run an external "git" command

    The 'command' attribute will be an array representing the
    command that failed and 'returncode' will contain the exit
    code of the command.  The 'stderr' member may contain the
    error output from the command, but may also be None."""

    def __init__(self, command, returncode, stderr=None):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        msg = "'%s' exited with code %d" % \
            (' '.join(command), returncode)
        if stderr:
            stderr = '\n  '.join(stripnl(stderr).split('\n'))
            msg += '\n\nError output of %s command:\n  %s' % \
                (command[0], stderr)
        super(GitCommandError, self).__init__(msg)

class Git(object):
    """Git repository and optional work tree.

    The Git repository may or may not already exist until the init()
    method is called, after which the repository will definitely
    exist, if the call returns successfully.
    """

    def __init__(self, directory=None):
        """Construct a Git repository object.
        """
        if directory == None:
            self._directory = os.getcwd()
        else:
            self._directory = directory

    def get_directory(self):
        """Return the repository top-level path.

        This may be the metadata directory or the top-level of the
        work tree depending on whether the repository is bare or not.

        This method may be called before the repository has been
        initialized and will always return the same result.
        """
        return self._directory

    directory = property(get_directory)

    def is_bare(self):
        """Return True iff the repository exists and is bare.

        This method may be called before the repository has been
        initialized, but may return a different result.
        """
        return self.config_get('core.bare') == 'true'

    def get_git_dir(self):
        """Return the path to the metadata directory.

        This method may be called before the repository has been
        initialized, but may return a different result.
        """
        if self.is_bare():
            return self.directory
        else:
            return os.path.join(self.directory, '.git')

    git_dir = property(get_git_dir)

    def get_git_work_tree(self):
        """Return the path to the working tree.

        If the repository is bare, None is returned since it has no
        associated work tree.

        This method may be called before the repository has been
        initialized, but may return a different result.
        """
        if self.is_bare():
            return None
        else:
            return self.directory

    git_work_tree = property(get_git_work_tree)

    def _popen(self, command, **kwargs):
        if not kwargs.has_key('env'):
            kwargs['env'] = safe_environ()
        if not kwargs.has_key('cwd'):
            kwargs['cwd'] = self.directory
        return Popen(command, **kwargs)

    def init(self, bare=False, quiet=False):
        """Initialize or reinitialize the repository.
        """
        args = []
        if bare:
            args.append('--bare')
        if quiet:
            args.append('--quiet')

        directory_created = False
        try:
            if not os.path.isdir(self.directory):
                os.mkdir(self.directory)
                directory_created = True

            command = ['git', 'init'] + args
            pipe = self._popen(command, stderr=PIPE)
            dummy, stderr = pipe.communicate()
            if pipe.returncode != 0:
                raise GitCommandError(command, pipe.returncode, stderr)
        except:
            if directory_created:
                shutil.rmtree(self.directory)
            raise

    def destroy(self):
        """Recursively remove the repository directory.
        """
        if os.path.exists(self.directory):
            shutil.rmtree(self.directory)

    def checkout(self, *args):
        """Call 'git checkout' with given arguments.
        """
        self.check_command('checkout', *args)

    def rebase(self, *args):
        """Call 'git rebase' with given arguments.
        """
        self.check_command('rebase', *args)

    def pull(self, *args):
        """Call 'git pull' with given arguments.
        """
        self.check_command('pull', *args)

    def rev_parse(self, *args):
        """Return the output of 'git rev-parse <*args>'
        """
        return self.check_command('rev-parse', *args, stdout=PIPE)

    def rev_list(self, *args):
        """Return the output of 'git rev-list <*args>'
        """
        return self.check_command('rev-list', *args, stdout=PIPE)

    def symbolic_ref(self, *args):
        """Return the output of 'git symbolic-ref <*args>'
        """
        return self.check_command('symbolic-ref', *args, stdout=PIPE)

    def check_command(self, command, *args, **kwargs):
        """Run "git" subcommand with given arguments.

        Raises a GitCommandError if the subcommand does not return a
        zero exit code.

        The stdout keyword argument can take any value that
        subprocess.Popen would accept.  If it is subprocess.PIPE, then
        the output of the command is returned as a string.
        """
        stdout = None
        for kw in kwargs.keys():
            if kw == 'stdout':
                stdout = kwargs[kw]
            else:
                raise ArgumentError, 'Invalid keyword: %s' % kw

        command = ['git', command] + list(args)
        pipe = self._popen(command, stdout=stdout, stderr=PIPE)
        out, err = pipe.communicate()
        if pipe.returncode != 0:
            raise GitCommandError(command, pipe.returncode, err)
        if stdout == PIPE:
            return stripnl(out)

    def config_get(self, varname, default=None):
        """Retrieve the value of a config variable.

        This method may be called before the repository exists.  In
        that case it will always return the default value.
        """
        if not os.path.isdir(self.directory):
            return default
        command = ['git', 'config', '--get', varname]
        pipe = self._popen(command, stdout=PIPE, stderr=PIPE)
        stdout, stderr = pipe.communicate()
        if pipe.returncode == 0:
            return stripnl(stdout)
        elif pipe.returncode == 1:
            return default
        else:
            raise GitCommandError(command, pipe.returncode, stderr)

    def config_set(self, varname, value):
        """Set the value of a config variable.
        """
        self.check_command('config', varname, value)

    def import_changesets(self, changesets, branch, domain=None,
                          limit=None, verbose=False,
                          progress=None, total=None):
        """Loop over changesets and import them.
        """
        if progress == None:
            progress = NoProgress()
        with progress:
            self._import_changesets(changesets, branch, domain,
                                    limit, verbose, progress,
                                    total)

    def _import_changesets(self, changesets, branch, domain, limit,
                           verbose, progress, total):
        message = _('Importing changesets')
        def do_progress(count, total):
            progress(message, len(changesets_seen), total)

        class SignalIndicator():
            def __init__(self):
                self.signal = {}
            def __call__(self, signalnum, frame):
                self.signal[signalnum] = True
            def isset(self, signalnum=None):
                if signalnum:
                    return self.signal.has_key(signalnum)
                else:
                    return len(self.signal) > 0

        sigaction = SignalIndicator()
        signalset = (SIGHUP,SIGINT,SIGTERM,)
        old_sigaction = {}
        for signalnum in signalset:
            old_sigaction[signalnum] = signal(signalnum, sigaction)

        def ignore_signals():
            for signalnum in signalset:
                signal(signalnum, SIG_IGN)

        # absolulte file name since cwd is changed in _popen
        marksfile = os.path.join(self.git_dir, 'cvsgit.marks')
        marksfile = os.path.abspath(marksfile)

        command = ['git', 'fast-import', '--quiet']
        command.append('--export-marks=' + marksfile)
        pipe = self._popen(command, stdin=PIPE, preexec_fn=ignore_signals)

        if limit != None and total != None and total > limit:
            total = limit

        fi = GitFastImport(pipe, branch, domain=domain, verbose=verbose)
        changesets_seen = []
        try:
            for changeset in changesets:
                if limit != None and len(changesets_seen) >= limit:
                    break

                changesets_seen.append(changeset)
                fi.add_changeset(changeset)
                do_progress(len(changesets_seen), total)

                if sigaction.isset(SIGINT):
                    raise KeyboardInterrupt()
                elif sigaction.isset():
                    break
        finally:
            try:
                fi.close()
            finally:
                self.mark_changesets(changesets_seen)
                for signalnum in signalset:
                    signal(signalnum, old_sigaction[signalnum])

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
    def __init__(self, pipe, branch, domain=None, verbose=False):
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

        self.write('commit %s\n' % self.branch)
        self.write('mark :%s\n' % changeset.id)
        self.write('committer %s <%s> %s\n' % (name, email, when))
        self.data(changeset.log.encode('utf-8'))

        if changeset.id != 1:
            # FIXME: this is a hack; find out if the branch exists
            if self.last_changeset is None:
                self.write('from %s^0\n' % self.branch)
            else:
                self.write('from :%s\n' % self.last_changeset.id)
        self.last_changeset = changeset

        for c in changeset.changes:
            if self.verbose:
                print '\t%s %s %s' % (c.filestatus, c.filename, c.revision)
            if c.filestatus == FILE_DELETED:
                self.write('D %s\n' % c.filename)
            else:
                blob = changeset.blob(c)
                perm = changeset.perm(c)

                # Git according to git-fast-import(1) only supports
                # these two file modes for plain files.
                if (perm & 0111) != 0:
                    perm = 0755
                else:
                    perm = 0644

                self.write('M %o inline %s\n' % (perm, c.filename))
                self.data(blob)

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
        assert type(data) == types.StringType, \
            "data type is %s" % type(data)
        self.write('data %d\n' % len(data))
        self.write(data)
        self.write('\n')

    def write(self, data):
        self.pipe.stdin.write(data)
