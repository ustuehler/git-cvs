PYTHON?=python

all: build

build:
	${PYTHON} setup.py build

clean:
	${PYTHON} setup.py clean
	rm -rf build
	rm -rf .coverage coverage.xml
	rm -f nosetests.xml
	rm -f pylint.txt

test:
	nosetests --with-doctest --with-xunit

coverage:
	coverage run tests/run.py --with-xunit
	coverage xml

lint:
	-pylint -f parseable cvsgit > pylint.txt

.PHONY: all build clean test coverage lint
