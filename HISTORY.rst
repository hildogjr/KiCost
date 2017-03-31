.. :changelog:

History
-------

0.1.34 (2017-03-31)
______________________

* Fixed crash caused by uninitialized array in Digikey webscraping module.
* Place any available scraped part info into spreadsheet even if part is not available from a distributor. 
* Removed unused imports from distributor modules.


0.1.33 (2017-02-23)
______________________

* Surround worksheet name with quotes in case it contains spreadsheet operators.
* Fixed extraction of product links from Farnell product tables.


0.1.32 (2017-02-14)
______________________

* Added options for including or excluding distributors.
* Updated web scrapers for various distributors.
* Added more debugging/logger statements.
* Updated some of the package requirements.


0.1.31 (2016-11-14)
______________________

* Giacinto Luigi Cerone added support for distributors Farnell and RS. 


0.1.30 (2016-11-07)
______________________

* Manufacturer's part number field can now be labeled as 'manf#', 'mpn', 'pn', '#', etc. (See documentation.)
* Manufacturer field can now be labeled as 'manf' or 'manufacturer'.
* Distributor part number fields can now be labeled as 'digikey#', 'digikeypn', digikey_pn', 'digikey-pn', etc. 


0.1.29 (2016-08-27)
______________________

* KiCost no longer fails if the <libparts>...</libparts> section is missing from the XML file.
* Documentation moved to Github Pages.


0.1.28 (2016-08-18)
______________________

* Fixed scraping of Digi-Key pages to correctly detect reeled parts and scrape alternate packaging options.


0.1.27 (2016-07-26)
______________________

* Fixed scraping of Digi-Key pages to correctly extract available quantity of parts.


0.1.26 (2016-07-25)
______________________

* Progress bar is explicitly deleted to prevent an error from occurring when the program terminates.


0.1.25 (2016-06-12)
______________________

* Contents of "Desc" field in component/library were being ignored when generating spreadsheet.


0.1.24 (2016-05-28)
______________________

* Fixed part scraping from Newark website.


0.1.23 (2016-04-12)
______________________

* Added progress bar.
* Added quiet option to suppress warning messages.
* 'manf#' and 'manf' fields are now both propagated to similar parts.


0.1.22 (2016-04-08)
______________________

* Extra part data can now be shown in the global data section of the spreadsheet
  by using the new ``--fields`` command-line option. This commit implements 
  issue #8.


0.1.21 (2016-03-20)
______________________

* Parts with valid Digi-Key web pages were not appearing in the spreadsheet
  because they had strange quantity listings (e.g., input fields or 'call for
  quantities'. This commit fixes #36.


0.1.20 (2016-03-20)
______________________

* Prices of $0.00 were appearing in the spreadsheet for parts that were
  listed but not stocked. Parts having no pricing list no longer list a price
  in the sheet.
* Parts with short manf. numbers (e.g. 5010) were not found correctly in the
  distributor websites. The manufacturer name was added to the search string
  to increase the probability of the search finding the correct part.


0.1.19 (2016-02-12)
______________________

* Local parts weren't showing up in spreadsheet because of previous fix to
  omit parts that had no quantity field (non-stocked; not even 0). Fixed.


0.1.18 (2016-02-10)
______________________

* Made change to adapt to change in Digi-Key's part quantity field of their webpages.
* Omit parts from the spreadsheet that are listed but not stocked at a distributor.


0.1.17 (2016-02-09)
______________________

* Made changes to adapt to changes in Digi-Key's webpage format.


0.1.16 (2016-01-26)
______________________

* Added ``--variant`` command-line option for costing different variants of a single schematic.
* Added ``--num_processes`` command-line option for setting the number of parallel 
  processes used to scrape part data from the distributor web sites.
* Added ``--ignore_fields`` command-line option for ignoring benign fields that might
  prevent identical parts from being grouped together.


0.1.15 (2016-01-10)
______________________

* Fixed exception caused when indexing with 'manf#' on components that didn't
  have that field defined.
* Replaced custom debug_print() with logging module.


0.1.14 (2015-12-31)
______________________

* When scraping a Digi-Key product list page, use both the manfufacturer's AND 
  Digi-Key's number to select the closest match to the part number.


0.1.13 (2015-12-29)
______________________

* 'kicost:' can be prepended to schematic field labels to distinguish them from other app fields.
* Custom prices and documentation links can now be added to parts in the schematic.
* Web-scraping for part data is sped up using parallel processes.

0.1.12 (2015-12-03)
______________________

* Following the IP address mouser with redirect you to the nearest locale match, 
  so the price will be in Euro if you are in Europe and the price decimal can be a comma.

0.1.11 (2015-12-02)
______________________

* Changed BOARD_COST field to UNIT_COST.
* Changed formatting of UNIT_COST field to make use monetary units.
* Changed format of debug messages.

0.1.10 (2015-10-08)
______________________

* Pushed lxml requirement back to 3.3.3 so linux mint would have fewer problems trying to install.

0.1.9 (2015-09-26)
______________________

* Fixed exception caused by Digi-Key part with 'call' as an entry in a part's price list.
* Fixed extraction of part quantities in Mouser web pages.
* Added randomly-selected user-agent strings so sites might be less likely to block scraping.
* Added ghost.py code for getting around Javascript challenge pages (currently inactive).

0.1.8 (2015-09-17)
______________________

* Added missing requirements for future and lxml packages.

0.1.7 (2015-08-26)
______________________

* KiCost now runs under both Python 2.7.6 and 3.4.

0.1.6 (2015-08-26)
______________________

* Mouser changed their HTML page format, so I changed their web scraper.

0.1.5 (2015-07-25)
______________________

* Corrected entrypoint in __main__.py.

0.1.4 (2015-07-09)
______________________

* Added conditional formatting to indicate which distributor had the best price for a particular part.
* Fixed calc of min unit price so it wouldn't be affected if part rows were sorted.

0.1.3 (2015-07-07)
______________________

* Added global part columns that show minimum unit and extended prices for all parts across all distributors.

0.1.2 (2015-07-04)
______________________

* Refactoring.
* To reduce the effort in adding manufacturer's part numbers to a schematic, one will now be assigned to a part if:

  #. It doesn't have one.
  #. It is identical to another part or parts which do have a manf. part number.
  #. There are no other identical parts with a different manf. part number than the ones in item #2.

0.1.1 (2015-07-02)
______________________

* Fixed delimiter for Mouser online order cut-and-paste.

0.1.0 (2015-06-30)
______________________

* First release on PyPI.
