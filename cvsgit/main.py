"""Main application class and user interface helper routines for
'git-cvs'."""

import os.path
import sys
import time

import cvsgit.cmd
from cvsgit.error import Error
from cvsgit.git import Git
from cvsgit.cvs import CVS
from cvsgit.meta import MetaDb
from cvsgit.i18n import _
from cvsgit.term import Progress

Command = cvsgit.cmd.Cmd

class ConduitError(Error):
    """Base exception for errors in the cvsgit.main module
    """

class NoSourceError(ConduitError):
    """Raised when no CVS source has been configured
    """
    def __init__(self):
        super(NoSourceError, self).__init__(
            _("missing 'cvs.source' in Git config"))

class Conduit(object):

    def __init__(self, directory=None):
        self.git = Git(directory)
        self._cvs = None
        self._config = {}

    def config_get(self, varname):
        if self._config.has_key(varname):
            return self._config[varname]
        else:
            value = self.git.config_get('cvs.' + varname)
            self._config[varname] = value
            return value

    def config_set(self, varname, value):
        self.git.config_set('cvs.' + varname, value)
        self._config[varname] = value

    def get_source(self):
        source = self.config_get('source')
        if source is None:
            raise NoSourceError
        return source

    def set_source(self, directory):
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
        self.source = repository
        if domain:
            self.domain = domain

    def fetch(self, count=None, quiet=True, verbose=False):
        params = {}
        params['domain'] = self.domain
        params['verbose'] = verbose
        #params['branch'] = 'refs/remotes/git-cvs'

        progress = Progress(enabled=not quiet and not verbose)

        progress(_('Counting files'), 0, 1) # XXX
        self.cvs.pull_changes(onprogress=lambda count, total:
            progress(_('Parsing RCS files'), count, total))

        self.cvs.generate_changesets(onprogress=lambda count, total:
            progress(_('Calculating changesets'), count, total))

        self.cvs.export_changesets(self.git, params, count=count,
            onprogress=lambda count, total:
                progress(_('Importing changesets'), count, total))
