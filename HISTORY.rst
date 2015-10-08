.. :changelog:

History
-------

0.1.10 (2015-10-08)
---------------------

* Pushed lxml requirement back to 3.3.3 so linux mint would have fewer problems trying to install.

0.1.9 (2015-09-26)
---------------------

* Fixed exception caused by Digi-Key part with 'call' as an entry in a part's price list.
* Fixed extraction of part quantities in Mouser web pages.
* Added randomly-selected user-agent strings so sites might be less likely to block scraping.
* Added ghost.py code for getting around Javascript challenge pages (currently inactive).

0.1.8 (2015-09-17)
---------------------

* Added missing requirements for future and lxml packages.

0.1.7 (2015-08-26)
---------------------

* KiCost now runs under both Python 2.7.6 and 3.4.

0.1.6 (2015-08-26)
---------------------

* Mouser changed their HTML page format, so I changed their web scraper.

0.1.5 (2015-07-25)
---------------------

* Corrected entrypoint in __main__.py.

0.1.4 (2015-07-09)
---------------------

* Added conditional formatting to indicate which distributor had the best price for a particular part.
* Fixed calc of min unit price so it wouldn't be affected if part rows were sorted.

0.1.3 (2015-07-07)
---------------------

* Added global part columns that show minimum unit and extended prices for all parts across all distributors.

0.1.2 (2015-07-04)
---------------------

* Refactoring.
* To reduce the effort in adding manufacturer's part numbers to a schematic, one will now be assigned to a part if:

  #. It doesn't have one.
  #. It is identical to another part or parts which do have a manf. part number.
  #. There are no other identical parts with a different manf. part number than the ones in item #2.

0.1.1 (2015-07-02)
---------------------

* Fixed delimiter for Mouser online order cut-and-paste.

0.1.0 (2015-06-30)
---------------------

* First release on PyPI.
