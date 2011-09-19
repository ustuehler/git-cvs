#!/usr/bin/env python

"""Python Distutils setup script for 'git-cvs'."""

from distutils.core import setup

setup(name='git-cvs',
      version='0.0.1',
      description='Import changesets from CVS into Git',
      author='Uwe Stuehler',
      author_email='uwe@bsdx.de',
      url='https://github.com/ustuehler/git-cvs',
      license='OpenBSD',
      packages=['cvsgit', 'cvsgit.command'],
      scripts=['scripts/git-cvs'],
      data_files=[('/usr/local/libexec/git', ['scripts/git-cvs'])])
