.. :changelog:

History
-------

0.1.21 (2016-03-20)
---------------------

* Parts with valid Digi-Key web pages were not appearing in the spreadsheet
  because they had strange quantity listings (e.g., input fields or 'call for
  quantities'. This commit fixes #36.


0.1.20 (2016-03-20)
---------------------

* Prices of $0.00 were appearing in the spreadsheet for parts that were
  listed but not stocked. Parts having no pricing list no longer list a price
  in the sheet.
* Parts with short manf. numbers (e.g. 5010) were not found correctly in the
  distributor websites. The manufacturer name was added to the search string
  to increase the probability of the search finding the correct part.


0.1.19 (2016-02-12)
---------------------

* Local parts weren't showing up in spreadsheet because of previous fix to
  omit parts that had no quantity field (non-stocked; not even 0). Fixed.


0.1.18 (2016-02-10)
---------------------

* Made change to adapt to change in Digi-Key's part quantity field of their webpages.
* Omit parts from the spreadsheet that are listed but not stocked at a distributor.


0.1.17 (2016-02-09)
---------------------

* Made changes to adapt to changes in Digi-Key's webpage format.


0.1.16 (2016-01-26)
---------------------

* Added ``--variant`` command-line option for costing different variants of a single schematic.
* Added ``--num_processes`` command-line option for setting the number of parallel 
  processes used to scrape part data from the distributor web sites.
* Added ``--ignore_fields`` command-line option for ignoring benign fields that might
  prevent identical parts from being grouped together.


0.1.15 (2016-01-10)
---------------------

* Fixed exception caused when indexing with 'manf#' on components that didn't
  have that field defined.
* Replaced custom debug_print() with logging module.


0.1.14 (2015-12-31)
---------------------

* When scraping a Digi-Key product list page, use both the manfufacturer's AND 
  Digi-Key's number to select the closest match to the part number.


0.1.13 (2015-12-29)
---------------------

* 'kicost:' can be prepended to schematic field labels to distinguish them from other app fields.
* Custom prices and documentation links can now be added to parts in the schematic.
* Web-scraping for part data is sped up using parallel processes.

0.1.12 (2015-12-03)
---------------------

* Following the IP address mouser with redirect you to the nearest locale match, 
  so the price will be in Euro if you are in Europe and the price decimal can be a comma.

0.1.11 (2015-12-02)
---------------------

* Changed BOARD_COST field to UNIT_COST.
* Changed formatting of UNIT_COST field to make use monetary units.
* Changed format of debug messages.

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
