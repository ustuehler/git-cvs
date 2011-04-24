PYTHON?=python

all: test

test:
	@for f in test/test_*.py; do \
	    env PYTHONPATH=`pwd` ${PYTHON} $$f; \
	done

.PHONY: all test
