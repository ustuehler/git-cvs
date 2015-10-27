#!/usr/bin/env python

"""Python Distutils setup script for 'git-cvs'."""

from setuptools import setup

setup(name='git-cvs',
      version='0.1.0',
      description='Import changesets from CVS into Git',
      author='Uwe Stuehler',
      author_email='uwe@bsdx.de',
      url='https://github.com/ustuehler/git-cvs',
      license='OpenBSD',
      packages=['cvsgit', 'cvsgit.command'],
      scripts=['scripts/git-cvs'],
      data_files=[('/usr/local/libexec/git', ['scripts/git-cvs'])],
      # XXX: a fairly recent version is required, but rcsparse
      # doesn't maintain a package version
      requires=['rcsparse'],
      test_suite='nose.collector',
      setup_requires=['nose>=1.0'])
