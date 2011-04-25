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
	nosetests --with-xunit --with-doctest

coverage:
	nosetests --with-xunit --with-doctest --with-coverage --cover-erase --cover-inclusive --cover-package=cvsgit
	coverage xml

lint:
	-pylint --rcfile scripts/pylintrc -i yes -f parseable cvsgit > pylint.txt

.PHONY: all build clean test coverage lint
