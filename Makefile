PYTHON?=python3
PYTEST?=pytest-3

.PHONY: clean-pyc clean-build docs clean update-rates

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests using PyTest (PYTEST env. var)"
	@echo "test-all - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "release - package and upload a release"
	@echo "dist - package"
	@echo "install - install the package to the active Python's site-packages"
	@echo "release-test test of release at https://test.pypi.org/ server"
	@echo "update-rates - update the currency exchange rates"
	@echo "deb - create a Debian package"
	@echo "deb-clean - clean after making a Debian package"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	@find . -name '*.egg-info' -exec rm -fr {} +
	@find . -name '*.egg' -exec rm -f {} + ; echo 1

clean-pyc:
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +
	@find . -name '*~' -exec rm -f {} +
	@find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	-rm -fr .tox/
	-rm -f .coverage
	-rm -fr htmlcov/


#
# lint
#  Check the coding style of this project
#  Note: `flake8` configurations are set in `.flake8`
#
.PHONY: lint
lint:
	flake8


test: lint
	$(PYTEST)

test-all:
	tox

coverage:
	coverage run --source kicost setup.py test
	coverage report -m
	coverage html
	open htmlcov/index.html

docs:
	rm -f docs/kicost.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ kicost
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	open docs/_build/html/index.html
	$(MAKE) -C ./docs/make singlehtml

release-test: clean
	$(PYTHON) setup.py sdist
	$(PYTHON) setup.py bdist_wheel
	twine upload --verbose --repository-url https://test.pypi.org/legacy/ dist/*

release: update-rates
	#clean
	#$(PYTHON) setup.py sdist upload
	#$(PYTHON) setup.py bdist_wheel upload
	twine upload --verbose dist/*

dist: update-rates clean
	$(PYTHON) setup.py sdist
	$(PYTHON) setup.py bdist_wheel
	ls -l dist

install: clean
	$(PYTHON) setup.py install

update-rates:
	$(PYTHON) tools/get_rates.py > kicost/currency_converter/default_rates.py
	$(PYTHON) tools/gen_currency_tables.py > kicost/currency_converter/currency_tables.py

deb: update-rates
	DEB_BUILD_OPTIONS=nocheck fakeroot dpkg-buildpackage -uc -b

deb-clean: clean
	fakeroot debian/rules clean
