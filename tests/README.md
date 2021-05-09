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
* Run a specific tests with detailed information.
```bash
pytest-3 --log-cli-level debug -k test_300_010
```
* List information about available tests
```bash
pytest-3 -co
```

# Creating tests

## Using a script

Some tests may be easier to generate using a script.
See `../tools/genGroupTest.sh` and  `../tools/genPartsAndCommentsTest.sh` for examples.


## Storing KitSpace values as test values.

1. In `test_kicost.py` define `ADD_QUERY_TO_KNOWN` to `1`
2. Run the test
3. Check you got the queries recorded in `tests/kitspace_queries.txt`
3. Revert `ADD_QUERY_TO_KNOWN` to `0`

Now you'll get the recorded replies

## Generating reference tests

We usually compare the generated, stored in `result_test/', with the references, stored in `expected_test/`.
Changing `CREATE_REF` to `1` in `test_kicost.py` creates the `expected_test/` assuming the code is running perfect.
