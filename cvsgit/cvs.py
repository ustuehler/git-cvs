"""CVS interface for CVSGit."""

import os.path
import re

from subprocess import Popen, PIPE

from cvsgit.changeset import ChangeSetGenerator
from cvsgit.rcs import RCSFile
from cvsgit.i18n import _

class CVS(object):
    "Represents a CVS repository."

    def __init__(self, metadb):
        self.metadb = metadb

        # 'dirname' is a local filesystem path pointing at the root of
        # a CVS repository or at a module within.  If it is a module
        # path, operations will be limited to that module.  Otherwise,
        # the module path will be empty and operations will by default
        # apply to the whole repository.
        #
        # In any case, the repository path is always determined by
        # recursively following the parents of 'dirname' until a a
        # sub-directory named 'CVSROOT' is found.  Repository path and
        # module path are available for reading in the instance
        # attributes 'root' and 'module', respectively.

        dirname = self.metadb.source
        if not os.path.isdir(dirname):
            raise TypeError, _('not a CVS repository path (%s): %s') \
                % (_('not even a directory'), dirname)

        # Convert to absolute pathname, so that our logic doesn't
        # break if anyone uses os.chdir() and so that the path
        # traversal below can always assume an absolute path.
        dirname = os.path.abspath(dirname)

        # Split 'dirname' into self.root and self.module and also
        # set self.prefix to the full absolute module path.
        cvsroot = dirname
        module = ''
        while True:
            parent = os.path.dirname(cvsroot)
            if cvsroot == parent:
                raise TypeError, _('not a CVS repository path (%s): %s') \
                    % (_('no CVSROOT within nor above'), dirname)
            if os.path.isdir(os.path.join(cvsroot, 'CVSROOT')):
                break
            if module == '':
                module = os.path.basename(cvsroot)
            else:
                module = os.path.join(os.path.basename(cvsroot), module)
            cvsroot = parent
        self.root = cvsroot
        self.module = module
        self.prefix = os.path.join(self.root, self.module)

    def rcs_filenames(self):
        """Yield the relative pathnames of all RCS files found in the
        tracked CVS repository or module."""

        # Helper function to raise the OSError reported by os.walk().
        def raise_error(e): raise e

        for dirpath, dirnames, filenames in \
                os.walk(self.prefix, onerror=raise_error):
            # Convert from absolute to relative path.
            assert(dirpath.startswith(self.prefix))
            dirpath = dirpath[len(self.prefix)+1:]
            for filename in filenames:
                if filename.endswith(',v'):
                    yield(os.path.join(dirpath, filename))

    def changed_rcs_filenames(self):
        """Like rcs_filenames() but yields only the names of RCS files
        which have changed since the last time we pulled changes from
        them."""

        # TODO: skip unchanged RCS files
        for filename in self.rcs_filenames():
            yield(filename)

    def pull_changes(self):
        """Pull new revisions from the CVS repository and add them to
        the meta database."""

        for filename in self.changed_rcs_filenames():
            rcsfile = RCSFile(os.path.join(self.prefix, filename))
            # For the working copy path it does not matter if the RCS
            # file is in the 'Attic' directory or not, so strip it.
            filename = re.sub('(Attic/)?([^/]+),v$', '\\2', filename)
            for change in rcsfile.changes():
                # TODO: handle branches other than HEAD
                if change.revision.count('.') == 1:
                    # Record the file's actual working copy path
                    # instead of the RCS filename.
                    change.filename = filename
                    self.metadb.add_change(change)

    def generate_changesets(self):
        """Convert changes stored in the meta database into sets of
        related changes and store the resulting changesets in the meta
        database as well.  The individual changes referenced in a
        changeset will be deleted from the meta database."""

        csg = ChangeSetGenerator()
        for change in self.metadb.changes_by_timestamp():
            for cs in csg.integrate(change):
                self.metadb.add_changeset(cs)
        for cs in csg.finalize():
            self.metadb.add_changeset(cs)

    def changesets(self):
        """Yield changesets reconstructed earlier from individual file
        changes and stored in the meta database by the
        generate_changesets() method."""

        for changeset in self.metadb.changesets_by_start_time():
            changeset.provider = self
            yield(changeset)

    def blob(self, change):
        """Return the raw binary content of a file at the specified
        revision."""

        filename = change.filename + ',v'
        rcsfile = os.path.join(self.prefix, filename)
        if not os.path.isfile(rcsfile):
            rcsfile = os.path.join(self.prefix,
                os.path.dirname(filename), 'Attic',
                os.path.basename(filename))
        if not os.path.isfile(rcsfile):
            raise RuntimeError, _('no RCS file found for %s') % filename

        argv = ['co', '-q', '-p' + change.revision, rcsfile]
        output = Popen(argv, stdout=PIPE).communicate()[0]
        return output

    def mark_changeset(self, changeset):
        """Mark 'changeset' as having been committed to "the other
        VCS"."""

        assert(changeset.mark != None)
        self.metadb.mark_changeset(changeset)
