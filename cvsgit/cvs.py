"""CVS interface module for CVSGit."""

import os.path
from rcs import RCSFile
from i18n import _

class CVSROOT(object):
    "Represents a CVS repository."

    def __init__(self, repository):
        """'repository' must point either at the top-level directory
        of the CVS repository or at any module directory within the
        repository.  The root of the CVS repository is automatically
        determined by traversing the directory hierarchy upwards until
        a subdirectory called 'CVSROOT' is found."""

        if not os.path.isdir(repository):
            raise TypeError, _('not a CVS repository path (%s): %s') \
                % (_('not even a directory'), repository)

        # Convert to absolute pathname, so that our logic doesn't
        # break if anyone uses os.chdir() and so that the path
        # traversal below can always assume an absolute path.
        repository = os.path.abspath(repository)

        # Split 'repository' into self.root and self.module and also
        # set self.prefix to the full absolute module path.
        cvsroot = repository
        module = ''
        while True:
            parent = os.path.dirname(cvsroot)
            if cvsroot == parent:
                raise TypeError, _('not a CVS repository path (%s): %s') \
                    % (_('no CVSROOT within nor above'), repository)
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

    def revisions(self, onrcsfile=None):
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
                    if onrcsfile:
                        onrcsfile(rcsfile)
                    for revision in rcsfile.revisions():
                        yield(revision)
