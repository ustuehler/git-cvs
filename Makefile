PYTHON?=python

all: build

build:
	${PYTHON} setup.py build

clean:
	${PYTHON} setup.py clean
	rm -rf build

test:
	env PYTHONPATH=`pwd` ${PYTHON} tests/run.py

.PHONY: all build clean test
