[![Build Status](https://travis-ci.org/ustuehler/git-cvs.svg?branch=master)](http://travis-ci.org/ustuehler/git-cvs)

ADVANTAGES OVER PLAIN CVS(1) AND CVSSYNC(1)
===========================================

 * Easy viewing of committed diffs.  With cvsync(1) or by monitoring
   source-changes@ you get ChangeLog entries but they only contain the
   list of affected files and a log message, without even the revision
   numbers of the affected files.  In Git you can do

   $ git log

   to get what you get from the ChangeLog entries and

   $ git show HEAD~1

   to show the diff for the second to last commit.

 * See all subtree changes.

   $ git log -p sys/arch/i386

 * Check the status of the working copy really fast.  "cvs status" in
   /usr/src takes about X minutes on my laptop while "git status" takes
   only 1.2 seconds.

 * Pull upstream changes really fast.  "cvs update" in /usr/src takes
   X minutes on my laptop while a "git pull" takes only Y seconds.

 * To see what's new after a "git pull", including the actual diffs,
   you can use

   $ git log --stat -p ORIG_HEAD..

   This isn't possible with cvs(1) at all.

DRAWBACKS
=========

 * Git, on purpose, does not manage the mtime of checked out files in
   order to allow make(1) and similar tools to figure out which files
   must be rebuilt after switching branches.  cvs sets the mtime to
   the repository mtime whenever checkout/update creates a new file,
   but not if the file already exists.

 * A full clone of the Git repository for src is about 450 MB after
   "git repack -adF" in addition to the 780 MB for a complete checkout.

 * cvsync/rsync and cvsgit have to run somewhere, but that could be a
   dedicated server.

INSTALLATION AND DEPENDENCIES
=============================

You must have a fairly recent version of Simon Schubert's rcsparse
library, available in either of these locations:

 * http://ww2.fs.ei.tum.de/~corecode/hg/rcsparse/archive/tip.tar.bz2
 * https://gitorious.org/fromcvs/rcsparse/archive-tarball/master

On top of that, you may have to apply the supplied patch (from the
patches/ directory in the git-cvs source tree) to fix an issue with
memory exhaustion during checkout.

To install git-cvs, run ./setup.py:

 $ sudo ./setup.py install

WORKFLOW
========

Repository creation (assuming that /cvs/src is a local mirror of
the OpenBSD src repository, maintained with CVSync):

 * cd /usr/src
 * git-cvs init --domain=cvs.openbsd.org /cvs/src
 * git-cvs pull

Patch management

 * git checkout -b somebody/patch-subject cvs/HEAD
 * From mutt: |cd /usr/src; git am --directory=sys/dev -p0

Generating patches that apply with -p0:

 * git config diff.noprefix true

Configuration hints (see git-config(1)):

 * Automatically set rebase option for new branches with
   branch.autosetuprebase always|remote
 * Disable a/b prefix with diff.noprefix=true

LIBRARIES FOR PARSING RCS FILES AND OTHER RESOURCES
===================================================

 * http://gitorious.org/fromcvs/rcsparse (used here)
 * rcsparse from cvs2svn
 * tparse from ViewVC
 * http://gitorious.org/parsecvs
 * http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.151.8450
 * http://metalinguist.wordpress.com/2007/12/06/the-woes-of-git-gc-aggressive-and-how-git-deltas-work/
