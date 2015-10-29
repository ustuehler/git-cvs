Reproducible incremental CVS-to-Git conversion
==============================================

[![Build Status](https://travis-ci.org/ustuehler/git-cvs.svg?branch=master)](http://travis-ci.org/ustuehler/git-cvs)

Installation
------------

There is a port of git-cvs for OpenBSD. Run `pkg_add git-cvs` to install the
package.

To install git-cvs from source, ensure that you have a recent version of Simon
Schubert's [rcsparse library](https://github.com/corecode/rcsparse) installed
and then run setup.py:

```text
sudo ./setup.py install
```

Usage
-----

**Clone a local CVS repository into a Git repository.**

```text
git cvs clone /cvs/src
```

This will parse all RCS files, generate changesets and import those changesets
into Git.  Some metadata will be stored in `.git/cvsgit.db` and is required for
further incremental runs.

**Update the Git repository with recent changesets from CVS.**

```text
git cvs pull
```

The CVSROOT for this command is the same as when the repository was cloned
initially.  You can change the CVS repository location by modifying the
`cvs.source` option with git-config(1).

Caveats
-------

Git, on purpose, does not manage the mtime of checked out files in order to
allow make(1) and similar tools to figure out which files must be rebuilt after
switching branches.  cvs sets the mtime to the repository mtime whenever
checkout/update creates a new file, but not if the file already exists.
