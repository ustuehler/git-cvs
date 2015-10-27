"""Main application class and user interface helper routines for
'git-cvs'."""

import os.path
import re

from cvsgit.cmd import Cmd
from cvsgit.error import Error
from cvsgit.git import Git
from cvsgit.cvs import CVS
from cvsgit.meta import MetaDb
from cvsgit.i18n import _
from cvsgit.term import Progress

class Command(Cmd):
    """Base class for conduit commands
    """

    def add_authors_option(self):
        self.add_option('--authors', metavar='AUTHORS', help=\
            _("Map CVS committer login names to fullnames."))

    def finalize_authors_option(self):
        if not self.options.authors:
            return
        authors = {}
        with open(self.options.authors, 'r') as file:
            while True:
                line = file.readline().strip()
                if not line:
                    break

                match = re.match('([^\s]+)\s+(.+)', line)
                if match:
                    login, fullname = match.groups()
                    authors[login] = fullname
                else:
                    self.warn('invalid line in authors map: %s' % line)
            self.options.authors = authors

    def add_stop_on_unknown_author_option(self):
        self.add_option('--stop-on-unknown-author', action='store_true', help=\
            _("Abort the operation if any author mapping is missing."))

    def add_quiet_option(self):
        self.add_option('--quiet', action='store_true', help=\
            _("Only report error and warning messages."))

    def add_verbose_option(self):
        self.add_option('--verbose', action='store_true', help=\
            _("Display each changeset as it is imported."))

    def add_no_skip_latest_option(self):
        self.add_option('--no-skip-latest', action='store_true', help=\
            _("Import potentially incomplete changesets instead of retaining them for the next incremental import."))

class ConduitError(Error):
    """Base exception for errors in the cvsgit.main module
    """

class NoSourceError(ConduitError):
    """Raised when no CVS source has been configured

    This error may occur if you run git-cvs commands in a directory
    that has not been initialized with "git-cvs init".
    """
    def __init__(self):
        super(NoSourceError, self).__init__(
            _("'cvs.source' is unset; not a git-cvs repository?"))

class UnknownAuthorFullnames(ConduitError):
    """Raised when there is no known fullname for an author's login
    name and --stop-on-missing-author was given on the command-line.
    """

    def __init__(self, authors):
        msg = 'unknown authors: %s' % ', '.join(authors)
        super(ConduitError, self).__init__(msg)

class Conduit(object):
    """CVS-to-Git conduit logic
    """

    def __init__(self, directory=None):
        self.git = Git(directory)
        self.branch = 'refs/heads/cvs/HEAD'
        self._cvs = None
        self._config = {}

    def config_get(self, varname):
        """Get a Git variable from the 'cvs' section
        """
        if self._config.has_key(varname):
            return self._config[varname]
        else:
            value = self.git.config_get('cvs.' + varname)
            self._config[varname] = value
            return value

    def config_set(self, varname, value):
        """Set a Git variable in the 'cvs' section
        """
        self.git.config_set('cvs.' + varname, value)
        self._config[varname] = value

    def get_source(self):
        """Get the CVS repository source path
        """
        source = self.config_get('source')
        if source is None:
            raise NoSourceError
        return source

    def set_source(self, directory):
        """Set the CVS repository source path
        """
        self.config_set('source', directory)

    source = property(get_source, set_source)

    def get_domain(self):
        return self.config_get('domain')

    def set_domain(self, directory):
        self.config_set('domain', directory)

    domain = property(get_domain, set_domain)

    def get_cvs(self):
        if self._cvs == None:
            filename = os.path.join(self.git.git_dir, 'cvsgit.db')
            metadb = MetaDb(filename)
            self._cvs = CVS(self.source, metadb)
        return self._cvs

    cvs = property(get_cvs)

    def init(self, repository, domain=None, bare=False, quiet=True):
        self.git.init(bare=bare, quiet=quiet)

        if not self.git.is_bare() and \
                self.git.config_get('branch.master.remote') == None:
            self.git.config_set('branch.master.remote', '.')
            self.git.config_set('branch.master.merge', self.branch)
            self.git.config_set('branch.master.rebase', 'true')

        self.source = repository

        if domain:
            self.domain = domain

    def fetch(self, limit=None, quiet=True, verbose=False,
              flush=False, authors=None, stop_on_unknown_author=False):
        """Fetch new changesets into the CVS tracking branch.
        """
        if quiet or verbose:
            progress = None
        else:
            progress = Progress()

        self.cvs.fetch(progress=progress, limit=limit, flush=flush)

        # XXX: Should not access private self.cvs.metadb.
        if authors and stop_on_unknown_author:
            unknown = []
            for author in self.cvs.metadb.all_authors():
                if not authors.has_key(author):
                    unknown.append(author)
            if len(unknown) > 0:
                raise UnknownAuthorFullnames(unknown)

        self.git.import_changesets(self.cvs.changesets(), self.branch,
                                   domain=self.domain,
                                   limit=limit,
                                   verbose=verbose,
                                   progress=progress,
                                   total=self.cvs.count_changesets(),
                                   authors=authors,
                                   stop_on_unknown_author=\
                                       stop_on_unknown_author)

    def pull(self, limit=None, quiet=True, verbose=False, flush=False,
             authors=None, stop_on_unknown_author=False):
        self.fetch(limit=limit, quiet=quiet, verbose=verbose,
                   flush=flush, authors=authors, stop_on_unknown_author=
                   stop_on_unknown_author)

        args = []
        if quiet:
            args.append('--quiet')

        if self.git.is_bare():
          self.git.check_command('branch', '-f', 'master', self.branch)
        else:
          # XXX: --quiet is not enough if branch.<branch>.rebase is true
          #self.git.pull(*args)
          import subprocess
          self.git.check_command('pull', *args, stdout=subprocess.PIPE)
