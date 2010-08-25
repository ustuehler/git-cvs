"""CVS interface module for CVSGit."""

import os.path
from subprocess import Popen, PIPE
from cvsgit.rcs import RCSFile
from cvsgit.i18n import _

class CVSROOT(object):
    "Represents a CVS repository."

    def __init__(self, dirname):
        """'dirname' is a local filesystem path pointing at the root
        of a CVS repository or at a module within.  If it is a module
        path, operations will be limited to that module.  Otherwise,
        the module path will be empty and operations will by default
        apply to the whole repository.

        In any case, the repository path is always determined by
        recursively following the parents of 'dirname' until a a
        sub-directory named 'CVSROOT' is found.  Repository path and
        module path are available for reading in the instance
        attributes 'root' and 'module', respectively.
        """

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

    def revisions(self):
        "Parse RCS files and yield revisions."

        def raise_error(e): raise e

        for dirpath, dirnames, filenames in \
                os.walk(self.prefix, onerror=raise_error):

            assert(dirpath.startswith(self.prefix))
            dirpath = dirpath[len(self.prefix)+1:]

            for filename in filenames:
                if filename.endswith(',v'):
                    relpath = os.path.join(dirpath, filename)
                    rcsfile = RCSFile(relpath, prefix=self.prefix)
                    for r in rcsfile.revisions():
                        # TODO: handle branches other than HEAD
                        if r.revision.find('.') == \
                           r.revision.rfind('.'):
                            yield(r)

    def blob(self, filename, revision):
        """Return the raw binary content of a file at the specified
        revision."""

        filename += ',v'
        rcsfile = os.path.join(self.prefix, filename)
        if not os.path.isfile(rcsfile):
            rcsfile = os.path.join(self.prefix, 'Attic', filename)
        if not os.path.isfile(rcsfile):
            raise RuntimeError, _('no RCS file found for %s') % filename

        argv = ['co', '-q', '-p' + revision, rcsfile]
        output = Popen(argv, stdout=PIPE).communicate()[0]
        return output

