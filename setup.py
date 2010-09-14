#!/usr/bin/env python

"""Python Distutils setup script for 'git-cvs'."""

from distutils.core import setup

setup(name='git-cvs',
      version='0.1.0',
      description='Import changesets from CVS into Git',
      author='Uwe Stuehler',
      author_email='uwe@bsdx.de',
      url='http://bsdx.de/',
      license='LICENSE',
      packages=['cvsgit', 'cvsgit.command', 'cvsgit.rcsparse'])
