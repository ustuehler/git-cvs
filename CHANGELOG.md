# 0.2.0 (unreleased)

* Track RCS revisions for each commit in refs/notes/cvs. This can be used
  to construct an entire CVS working copy.

# 0.1.0

* Clone, fetch and pull will ignore the very last changesets because those
  could be incomplete. If you know that the CVS repository is consistent
  you may use --no-skip-latest to import every last of the changesets.

* Clone now runs "git repack" for a significantly smaller Git repository.

* Pull can be used in a bare repository and will simply update the master
  branch to match cvs/HEAD.

* The authors mapping file can now include an optional per-author e-mail.
  For example: `foo First Last <foo@example.com>`. Thanks to Jean-Philippe
  Ouellet.

* Unit tests for incremental conversion from various CVS repository states.

# 0.0.1

Initial version.
