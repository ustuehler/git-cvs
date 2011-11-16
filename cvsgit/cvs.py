"""CVS interface for CVSGit."""

import os.path
import re
import time

from subprocess import Popen, PIPE

from cvsgit.changeset import ChangeSetGenerator
from cvsgit.rcs import RCSFile
from cvsgit.i18n import _
from cvsgit.term import NoProgress
from cvsgit.utils import stripnl

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
        self._rcs_log_keyword_re = re.compile('(.*)\$Log(?::[^$\r\n]+)?\$(.*)')
        self._rcs_keyword_re = re.compile('\$([A-Z][A-Za-z]+)(:[^$\r\n]*)?\$')
        self._rcs_strip_attic_re = re.compile('(Attic/)?([^/]+),v$')

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
        # Helper function to raise the OSError reported by os.walk().
        def raise_error(e): raise e

        self.statcache = self.metadb.load_statcache()
        result = []
        count = 0

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

    def fetch_changes(self, progress=None):
        """Fetch new revisions from the CVS repository.
        """
        if progress == None:
            progress = NoProgress()

        filenames = self.changed_rcs_filenames(progress=progress)
        with progress:
            self._fetch_changes(filenames, progress)

    def _fetch_changes(self, filenames, progress):
        count = 0
        total = len(filenames)
        progress(_('Parsing RCS files'), count, total)

        # We will commit changes to the database every few seconds to
        # avoid having to scan all RCS files again in case the process
        # is interrupted or an error occurs (a rescan isn't really bad
        # but costs time.)
        commit_time = 0
        commit_interval = 10
        self.metadb.begin_transaction()
        for rcsfile in filenames:
            try:
                self._fetch_changes_from_rcsfile(rcsfile)

                if time.time() - commit_time >= commit_interval:
                    try:
                        self.metadb.end_transaction()
                    except:
                        pass
                    self.metadb.begin_transaction()
                    commit_time = time.time()

                count += 1
                progress(_('Parsing RCS files'), count, total)
            except KeyboardInterrupt:
                # Re-raise the exception silently.  An impatient user
                # may interrupt the process and that should by handled
                # gracefully.
                raise
            except:
                # Print the file name where this error happened,
                # regardless of whether the error is actually printed,
                # just as a quick & dirty debugging aid.
                # TODO: raise a FetchChangesError
                print "(Error while processing %s)" % rcsfile
                raise
            finally:
                try:
                    self.metadb.end_transaction()
                except:
                    pass

    def _fetch_changes_from_rcsfile(self, rcsfile):
        # For the working copy path it does not matter if the RCS
        # file is in the 'Attic' directory or not, so strip it.
        filename = self._rcs_strip_attic_re.sub('\\2', rcsfile)

        abspath = os.path.join(self.prefix, rcsfile)
        st = os.stat(abspath)
        identity = (st.st_mtime, st.st_size,)

        for change in RCSFile(abspath).changes():
            # Record the file's actual working copy path, which
            # RCS alone cannot know about.
            change.filename = filename
            self.metadb.add_change(change)

        self.metadb.update_statcache({rcsfile:identity})

    def generate_changesets(self, progress=None, limit=None):
        """Convert changes stored in the meta database into sets of
        related changes and store the resulting changesets in the meta
        database as well.
        """
        if progress == None:
            progress = NoProgress()

        with progress:
            count = 0
            csg = ChangeSetGenerator()
            total = self.metadb.count_changes()
            progress(_('Processing changes'), 0, total)
            for change in self.changes(processed=False, reentrant=True):
                count += 1
                progress(_('Processing changes'), count, total)
                for cs in csg.integrate(change):
                    # XXX: not reflected in progress output, and ugly
                    if limit:
                        if limit > 0:
                            limit -= 1
                        else:
                            return
                    self.metadb.add_changeset(cs)
            for cs in csg.finalize():
                # XXX: not reflected in progress output, and ugly
                if limit:
                    if limit > 0:
                        limit -= 1
                    else:
                        return
                self.metadb.add_changeset(cs)

    def fetch(self, progress=None, limit=None):
        """Fetch new revisions and compute changesets.
        """
        self.fetch_changes(progress)
        self.generate_changesets(progress, limit)

    def changesets(self):
        """Yield new changesets computed earlier.
        """
        for changeset in self.metadb.changesets_by_start_time():
            changeset.provider = self
            yield(changeset)

    def changes(self, processed=None, reentrant=True):
        """Yields changes fetched earlier.

        The 'processed' keyword can be set to a boolean value to
        select whether changes which are already included in a
        previously computed changeset are to be considered.  If the
        value is None, then all changes are considered.
        """
        return self.metadb.changes_by_timestamp(processed=processed,
                                                reentrant=reentrant)

    def rcsfilename(self, change):
        """Return the RCS filename corresponding to <change>.
        """
        filename = change.filename + ',v'

        result = os.path.join(self.prefix, filename)
        if os.path.isfile(result):
            return result

        result = os.path.join(self.prefix,
                              os.path.dirname(filename), 'Attic',
                              os.path.basename(filename))
        if os.path.isfile(result):
            return result

        raise RuntimeError, _('no RCS file found for %s') % \
            change.filename

    def rcsfile(self, change):
        """Return an RCSFile object for <change>.
        """
        return RCSFile(self.rcsfilename(change))

    def perm(self, change):
        """Return the file permissions as a decimal number.
        """
        return os.stat(self.rcsfilename(change)).st_mode & 0777

    def blob(self, change, changeset):
        """Return the raw binary content of a file at the specified
        revision.
        """
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
        #if change.revision == '1.1.1.1' and \
        #        change.timestamp < changeset.timestamp:
        #    revision = '1.1'
        #else:
        #    revision = change.revision
        revision = change.revision

        rcsfile = RCSFile(rcsfile)
        blob = rcsfile.blob(revision)
        return self.expand_keywords(blob, change, rcsfile, revision)

    def expand_keyword(self, change, rcsfile, revision, kw):
        if kw == 'Id' or (self.localid and kw == self.localid):
            return ('%s %s %s %s %s' %
                    (os.path.basename(rcsfile.filename),
                     revision, time.strftime('%Y/%m/%d %H:%M:%S',
                     time.gmtime(change.timestamp)), change.author,
                     change.state))
        elif kw == 'Header':
            return ('%s %s %s %s %s' %
                    (rcsfile.filename, revision,
                     time.strftime('%Y/%m/%d %H:%M:%S',
                     time.gmtime(change.timestamp)), change.author,
                     change.state))
        elif kw == 'Date':
            return time.strftime('%Y/%m/%d %H:%M:%S',
                                 time.gmtime(change.timestamp))
        elif kw == 'Revision':
            return revision
        elif kw == 'Source':
            return rcsfile.filename
        elif kw == 'Author':
            return change.author
        elif kw in 'RCSfile':
            return os.path.basename(rcsfile.filename)
        elif kw == 'Log':
            # additional lines get inserted elsewhere
            return os.path.basename(rcsfile.filename)
        elif kw == 'State':
            return change.state
        elif kw in ('Locker', 'Name'):
            return ''
        elif kw == 'Mdocdate': # for OpenBSD
            timestamp = time.gmtime(change.timestamp)
            mdocdate = time.strftime('%B %e %Y', timestamp)
            mdocdate = mdocdate.replace('  ', ' ') # for %e
            return mdocdate

    def expand_log_keyword(self, change, rcsfile, revision, prefix):
        timestamp = time.gmtime(change.timestamp)
        timestamp = time.strftime('%Y/%m/%d %H:%M:%S', timestamp)
        s = prefix + ('Revision %s  %s  %s\n' %
                      (revision, timestamp, change.author))
        log = stripnl(rcsfile.rcsfile.getlog(revision))
        for line in log.split('\n'):
            s += (prefix + line).rstrip() + '\n'
        s += prefix.rstrip()
        return s

    # Expand RCS keywords while avoiding to copy the whole file
    # content into a new object when there's nothing to expand.
    def expand_keywords(self, blob, change, rcsfile, revision):
        # Skip keyword expansion for binary mode files.
        if change.mode == 'b' or rcsfile.expand not in (None, '', 'kv'):
            return blob

        text = None
        start = blob.find('$')

        while start != -1:
            end = blob.find('$', start + 1)
            if end == -1:
                break

            s = blob[start:end + 1]
            m = self._rcs_keyword_re.match(s)
            if m:
                kw = m.group(1)
                s2 = self.expand_keyword(change, rcsfile, revision, kw)
                if s2 != None:
                    #print '%s: >>>%s<<<' % (rcsfile.filename, s2)
                    if text == None:
                        text = blob[0:start]
                    text += '$' + kw + ': ' + s2.encode('ascii') + ' '
                    if kw == 'Log':
                        end += 1
                        text += '$\n'
                        prefix = blob[blob.rfind('\n', 0, start) + 1:start]
                        text += self.expand_log_keyword(
                            change, rcsfile, revision, prefix
                            ).encode('ascii')
                elif text != None:
                    text += blob[start:end]
            elif text != None:
                text += blob[start:end]

            start = end

        if text != None:
            text += blob[start:]

        # Return the original input string or expanded version.
        if text == None:
            return blob
        else:
            return text

    def mark_changeset(self, changeset):
        """Mark 'changeset' as having been committed to "the other
        VCS"."""

        assert(changeset.mark != None)
        self.metadb.mark_changeset(changeset.id, changeset.mark)

    def count_changesets(self):
        return self.metadb.count_changesets()
