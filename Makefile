PYTHON?=python

all: test

test:
	env PYTHONPATH=`pwd` ${PYTHON} tests/run.py

.PHONY: all test
