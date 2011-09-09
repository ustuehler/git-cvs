"""CVS interface for CVSGit."""

import os.path
import re
import time

from subprocess import Popen, PIPE

from cvsgit.changeset import ChangeSetGenerator
from cvsgit.rcs import RCSFile
from cvsgit.i18n import _
from cvsgit.term import NoProgress

def split_cvs_source(dirname):
    """Split <dirname> into CVSROOT and module paths.
    """
    cvsroot = dirname
    module = ''
    while True:
        parent = os.path.dirname(cvsroot)
        if cvsroot == parent:
            raise TypeError, _('not a CVS repository path (%s): %s') \
                % (_('no CVSROOT within nor above'), dirname)
        if os.path.isdir(os.path.join(cvsroot, 'CVSROOT')):
            return (cvsroot, module,)
        if module == '':
            module = os.path.basename(cvsroot)
        else:
            module = os.path.join(os.path.basename(cvsroot), module)
        cvsroot = parent

class CVS(object):
    """Represents a CVS repository.
    """

    def __init__(self, dirname, metadb):
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

        if not os.path.isdir(dirname):
            raise TypeError, _('not a CVS repository path (%s): %s') \
                % (_('not even a directory'), dirname)

        # Convert to absolute pathname, so that our logic doesn't
        # break if anyone uses os.chdir() and so that the path
        # traversal below can always assume an absolute path.
        dirname = os.path.abspath(dirname)

        # Split 'dirname' into self.root and self.module and also
        # set self.prefix to the full absolute module path.
        self.root, self.module = split_cvs_source(dirname)
        if self.module == '':
            self.prefix = self.root
        else:
            self.prefix = os.path.join(self.root, self.module)

        self.localid = None
        self.parse_options()

        self.statcache = {}

    def parse_options(self):
        """Extract relevant information from the CVSROOT/options file,
        if it exsits.  At the moment, the only information that is
        used from the file is the custom Id tag keyword 'tag'."""

        filename = os.path.join(self.root, 'CVSROOT', 'options')
        if not os.path.isfile(filename):
            return

        f = file(filename, 'r')
        try:
            for line in f.readlines():
                option, value = line.split('=', 2)
                if option == 'tag':
                    self.localid = value.strip()
        finally:
            f.close()

    # Helper function to check with the statcache and the stat()
    # system call if a file or directory is unmodified.
    def _unmodified(self, path):
        st = os.stat(os.path.join(self.prefix, path))
        identity = (st.st_mtime, st.st_size,)
        return self.statcache.has_key(path) and \
                self.statcache[path] == identity

    def changed_rcs_filenames(self, progress=None):
        """Return the list of RCS filenames which need to be scanned for
        new changes to import.
        """
        if not progress:
            progress = NoProgress()

        with progress:
            return self._changed_rcs_filenames(progress=progress)

    def _changed_rcs_filenames(self, progress=None):
        progress(_('Collecting RCS files'))
        count = 0

        # Helper function to raise the OSError reported by os.walk().
        def raise_error(e): raise e

        self.statcache = self.metadb.load_statcache()
        result = []

        for dirpath, dirnames, filenames in \
                os.walk(self.prefix, onerror=raise_error):

            # Convert from absolute to relative path.
            assert(dirpath.startswith(self.prefix))
            dirpath = dirpath[len(self.prefix)+1:]

            # TODO: fill stat() cache for directories
            #if self._unmodified(dirpath):
            #    continue

            # Are we in an Attic directory? Then we must check each
            # filename for a "zombie" copy in the parent directory
            # and decide which one to use.
            in_attic = os.path.basename(dirpath) == 'Attic'
            if in_attic:
                parent = os.path.dirname(dirpath)

            for filename in filenames:
                # Ignore all non-RCS files.
                if not filename.endswith(',v'):
                    continue

                count += 1
                progress(_('Collecting RCS files'), count)

                #
                # Perform the zombie check:
                #
                # 1.) If the zombie is in the parent directory, remove
                #     it from 'result' and add the one in the Attic.
                #
                # 2.) If the zombie is in the Attic, leave the good one
                #     in 'result' and ignore the one in the Attic.
                #
                # 3.) If neither of the two files can be classified as
                #     a zombie, raise an error.
                #
                if in_attic and self._zombie_check(result, parent, filename):
                    # This is case 2.) above: skip the Attic filename.
                    continue

                filename = os.path.join(dirpath, filename)
                if not self._unmodified(filename):
                    result.append(filename)

        return result

    def _zombie_check(self, result, parent, filename):
        """Check a path for zombie files.  If a path exists in the Attic
        and the parent directory, one of them must be a zombie copy.  If
        it cannot be determined which one is the zombie and which one is
        the real copy, raise an error.

        This function should only be called during an os.walk() run when
        searching for files an Attic directory.  This guarantees that we
        have already seen the other copy in the parent directory, if one
        exists.  The return value is True if the zombie is in the Attic
        and False if the zombie is in the parent directory."""

        trunkfile = os.path.join(parent, filename)
        if not os.path.isfile(trunkfile):
            # No zombie present; the file exists only in Attic.
            return False

        atticfile = os.path.join(parent, 'Attic', filename)
        # FIXME: Not a reliable test. We should make sure that the
        # zombie contains a subset of the revisions of the real copy.
        if os.path.getsize(trunkfile) < os.path.getsize(atticfile):
            result.remove(trunkfile)
            return False

        raise RuntimeError, \
            _("invalid path: %s (%s)") % (trunkfile, \
            _('exists in Attic and parent directory'))

    def pull_changes(self, progress=None):
        """Pull new revisions from the CVS repository and add them to
        the meta database."""

        if progress == None:
            progress = NoProgress()

        filenames = self.changed_rcs_filenames(progress=progress)

        with progress:
            self._pull_changes(filenames, progress)

    def _pull_changes(self, filenames, progress):
        count = 0
        total = len(filenames)
        progress(_('Parsing RCS files'), count, total)

        for rcs_filename in filenames:
          try:
            # For the working copy path it does not matter if the RCS
            # file is in the 'Attic' directory or not, so strip it.
            filename = re.sub('(Attic/)?([^/]+),v$', '\\2', rcs_filename)

            rcs_abspath = os.path.join(self.prefix, rcs_filename)
            st = os.stat(rcs_abspath)
            identity = (st.st_mtime, st.st_size,)
            rcsfile = RCSFile(rcs_abspath)

            for change in rcsfile.changes():
                # Record the file's actual working copy path, which
                # RCS alone cannot know about.
                change.filename = filename
                self.metadb.add_change(change)

            # Flush changes to disk after each RCS file; otherwise,
            # interruption would cause us to scan RCS files again
            # (which isn't bad but costs time).
            self.metadb.update_statcache({rcs_filename:identity})
            self.metadb.commit()

            count += 1
            progress(_('Parsing RCS files'), count, total)
          except KeyboardInterrupt:
            raise
          except:
            # XXX: Print the file name where this error happened,
            # regardless of whether the error is actually printed,
            # just as a quick & dirty debugging aid.
            print "(Error while processing %s)" % rcs_filename
            raise

    def generate_changesets(self, progress=None):
        """Convert changes stored in the meta database into sets of
        related changes and store the resulting changesets in the meta
        database as well.
        """
        if progress == None:
            progress = NoProgress()

        progress(_('Calculating changesets'))
        with progress:
            count = 0
            total = self.metadb.count_changes()
            progress(_('Calculating changesets'), count, total)
            csg = ChangeSetGenerator()
            for change in self.metadb.changes_by_timestamp():
                count += 1
                progress(_('Calculating changesets'), count, total)
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

    def blob(self, change, changeset):
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

        # cvs has the odd behavior that it favors revision 1.1 over
        # 1.1.1.1 if it searches for a revision by date and the date
        # is after that of the initial revision even by one second.
        if change.revision == '1.1.1.1' and \
                change.timestamp < changeset.timestamp:
            revision = '1.1'
        else:
            revision = change.revision

        #
        # We use co(1) instead of cvs(1) to fetch the full text of a
        # particular revision since cvs(1) needs an existing working
        # copy (then we could use "cvs up -p -r <rev>").  The problem
        # with co(1) is that it does not expand RCS keywords in the
        # same way as cvs(1) would do.  In particular, co(1) will not
        # expand the "local ID" keyword that can be set through the
        # "tag=XYZ" option in CVSROOT/options.  We will do that here
        # but leave the rest of the keywords to be expanded by co(1).
        #
        argv = ['co', '-q', '-p' + revision, rcsfile]
        pipe = Popen(argv, stdout=PIPE)
        if change.mode == 'b':
            return pipe.communicate()[0]

        line = pipe.stdout.readline()
        data = ''
        while line:
            data += self.expand_keywords(line, change)
            line = pipe.stdout.readline()
        return data

    def expand_keywords(self, line, change):
        return re.sub('\$([^$:]+)[^$]*\$',
            lambda match: self.expand_keyword_match(match, change),
            line)

    def expand_keyword_match(self, match, change):
        if self.localid and match.group(1) == self.localid:
            timestamp = time.gmtime(change.timestamp)
            return ('$%s: %s,v %s %s %s %s $' % \
                (self.localid,
                 os.path.basename(change.filename),
                 change.revision,
                 time.strftime('%Y/%m/%d %H:%M:%S', timestamp),
                 change.author, change.state)).encode('ascii')
        elif match.group(1) == 'Mdocdate':
            timestamp = time.gmtime(change.timestamp)
            mdocdate = time.strftime('%B %e %Y', timestamp)
            mdocdate = mdocdate.replace('  ', ' ') # for %e
            return ('$Mdocdate: %s $' % mdocdate)
        else:
            return match.group(0)

    def mark_changeset(self, changeset):
        """Mark 'changeset' as having been committed to "the other
        VCS"."""

        assert(changeset.mark != None)
        self.metadb.mark_changeset(changeset)

    def count_changesets(self):
        return self.metadb.count_changesets()
