#!/bin/sh
time python cvsgit/command/clone.py \
  --domain=cvs.openbsd.org \
  --tz=Canada/Mountain \
  --incremental \
  --verbose \
  /cvs/src
