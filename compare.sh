#!/bin/sh

CVSROOT=/cvs
MODULE="${1:?missing <module> argument}"
BASENAME="`basename \"$MODULE\"`"

PYTHONPATH="`dirname \"$0\"`"
export PYTHONPATH

set -e

rm -rf "$BASENAME"-cvs "$BASENAME"-git

time python -m cvsgit.command.clone \
  --incremental \
  --progress \
  --verbose \
  "$CVSROOT/$MODULE" "$BASENAME"-git

cvs -q -d "$CVSROOT" co -P -d "$BASENAME"-cvs "$MODULE"

diff -r "$BASENAME"-cvs "$BASENAME"-git
