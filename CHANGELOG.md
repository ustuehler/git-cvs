# 0.1.0

* Clone now runs "git repack" for a significantly smaller Git repository.

* Clone, fetch and pull will ignore the very last changesets because those
  could be incomplete. If you know that the CVS repository is consistent
  you may use --no-skip-latest to import every last of the changesets.

* Pull can be used in a bare repository and will simply update the master
  branch to match cvs/HEAD.

* Unit tests for incremental conversion from various CVS repository states.

# 0.0.1

Initial version.
