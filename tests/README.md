# Some information about running tests

* Tests are contained in `test_kicost.py`
* Install requirements:  
```bash
pip install flake8 pytest xlsx2csv
```
* Run all tests  
```bash
pytest
```
* Run a specific tests (where `test_300_010` is a test function in `test_kicost.py`).
```bash
pytest -k test_300_010
```
* List information about available tests
```bash
pytest -co
```
