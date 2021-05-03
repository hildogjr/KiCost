# Some information about running tests

* Tests are contained in `test_kicost.py`
* Install requirements:  
```bash
pip install flake8 pytest xlsx2csv
```
on Debian, Ubuntu, etc. just install `flake8`, `python3-pytest` and `xlsx2csv` packages.
Don't use `pip`, unless you want to mess your system.
* They are supposed to be run from the root of the project
* You can just use:
```bash
make test
```
* Run all tests  
```bash
pytest-3
```
Or:
```bash
pytest
```
* Run a specific tests (where `test_300_010` is a test function in `test_kicost.py`).
```bash
pytest-3 -k test_300_010
```
* List information about available tests
```bash
pytest-3 -co
```
