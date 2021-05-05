.. :changelog:

History
-------

1.1.5 (2021-05-??)
______________________
* Fix the Farnell import code order
* Fix LCSC link and add BOM import links of all
* Add the user custom field capability to order quote
* Add cell size adjust algorithm (use --max_column_width 0 to disable it)
* Add ``pricing`` processing for subparts.
* Add ``--split_extra_fields`` to specify more fields to split for subparts.


1.1.4 (2020-03-24)
______________________
* Add TME and Arrow to Kitspace API.
* Others cosmetic and internal changes.


1.1.3 (2019-12-31)
______________________
* Fix the Digikey using Digi-Reel information.
* Added LCSC as distributor into the Kitspace API (the list can be used to JLCPCB).
* Parinfo kitspace API now just return the asked distributors (before was given all the avaliable distributors).


1.1.2 (2019-09-26)
______________________
* Check by accepted stock code into the API modules.
* Added ``--info`` command to get all the details of KiCost installation.
* Now ``--setup`` and ``--unsetup`` add and remove the default KiCost field to Eeschema template. ``--setup`` ran at the KiCost installation.
* Added a NEWS dialog on first GUI initialization.
* Fix in GUI: process bar, the not found module name, Windows open spreadsheet in the GUI and LibreOffice installation check on Windows.


1.1.1 (2019-08-16)
______________________
* Fix minimum order number and warning the user, it also show in the price break.
* Improve some spreadsheet formulas.
* Fix the Kitspace query API to prioritize the catalogue number under the manufacture code.
* Added a global field for purchase information, it will be added as description to be printed into the package labels (Digikey and others distributors that allow to include description into the package labels).
* Organized the distributors information for better KiCost next features in the road map.


1.1 (2019-07-15)
______________________
* Fix the issue of RST files in the PyPI package.
* Use the PartInfo KitSpace API.
* Creates a KiCad plugin integration and desktop shortcuts (not in Mac-OS) during the installation.
* Add KiCost to the context menu "Open with..." in Windows to XML and CSV files.
* Show (and allow to change in the spreadsheet) the current currency rate for distributors that are not in the specified currency.
* Highlight non-active in production / not-recommended-to-new-layout / decrepit components.
* Improved the spreadsheet purchase distributors code formula and fix the Digikey/Mouser import errors.
* Show the total purchased at the spreadsheet.
* Split the GUI file in programming one in wxFormBuilder generated.
* Fix the error when deal with spaces in the names of BOM files on `test.sh`.


1.0.4 (2018-10-02)
______________________
* Use the datasheet information distributor/API as link in ``manf#`` if not got any by the BOM.
* Added user warnings of bad ``manf`` format in case of multi-files of different quantities assigned on the catalogue codes.
* ``manf#`` cell get purple color if the distributor assigned the part as 'obsolete' or 'not recommended for new designs'.


1.0.3 (2018-10-06)
______________________
* Fix READ file on installation.


1.0.2 (2018-10-06)
______________________
* Fix the \*.md installation files.
* Minor modifications into the new class model.


1.0.1 (2018-10-05)
______________________

* Complete re-facture of internal class structure, now ``distributors`` and ``edas`` follow a heritage model.
* Add a ``post_setup`` function to configure shortcut and OS dependent settings.
* Fix some minor error with multi file projects.
* Fix the Octopart response with part with ``manf#`` but with ``distributor#``.
* Removed the limitation of subpart with empty ``manf#`` that doesn't respected the quantity.


1.0.0 (2018-10-03)
______________________

* Re-facture the KiCost motor, now use the Octopart API.
* Added a full currency convert capability.
* Fix some minor error with multi file projects.


0.1.47 (2018-08-16)
______________________

* Created the KiCad plugin (in beta).
* Fixed Digikey distributor module logger problem raise on refacture.
* Added GUI compatibility with wxPython 3.x.x.
* Added convert to ODS option if recognized LibreOffice in the system.
* Others GUI controls improvements.


0.1.46 (2018-07-04)
______________________

* Fixed some Python 2 incompatibility of the GUI and Altium module.
* Fixed the tqdm print channel. Now the process bar is kept at the end.
* Fixed the output messages when used the GUI.
* Fixed GUI problem caused by distributors re-factore and other UI improvements.
* More improvements on scrape classes.
* Now TME ajax post scrape method repect the ``fake_browser``.


0.1.45 (2018-06-12)
______________________

* Changed Farnell link and table result format.
* Fixed TME ``fake_browser`` migration.
* Re-factored the distributors modules to class kind and improved the scrape sequence to decrease probability of ban.
* Fixed the multi-threading configuration.
* Fixed Mac-OS hang when parallel scraping.


0.1.44 (2018-05-28)
______________________

* Fixed ``logging`` messages when using ``tqdm`` (process bar) for sequential scrape, missing fix for multithreads scrape.
* Improve the ``spreadsheet.py`` to a lighter file when use just one distributor.
* Improved log messages to better community debug.
* Add Upverter CSV compatibility.
* Fixed Mouser "quote price" exception in the price tiers.
* Fixed wxPython exception import.
* Use the datasheet link information from KiCad and other EDAs, given by 'datasheet' field.
* Now automatically merge 'description' and other fields to create the groups.
* GUI save last position and size and others improvements.
* Display additional information from the web page distributors and use as comment in the ``cat#`` column (just implemented on DigiKey yet).
* Now is possible to specify country/currency to be priorized on the distributors scrapes (just implemented on DigiKey yet).
* Minor improvements.


0.1.43 (2018-03-15)
______________________

* Fixed RS scrape module.
* Added ``--no_scrape`` option to create spreadsheets without information from distributor websites.
* Added ``--no_collapse`` option to prevent collapsing part references in the spreadsheet.
* Added ``--throttling_delay`` option to add delay between accesses to distributor websites. 
* Added ``--show_eda_list`` option to display the list of EDA tools supported by KiCost.
* Added capability to read multiple BOM files and merge them into the spreadsheet.
* Added ``--group_fields`` option to ignore differences in fields of the components and group them.
* Fixed the not ungrouping issue when ``manf#`` equal ``None``.
* CSV now accepts files from Proteus and Eagle EDA tools.
* Cleared up unused Python imports and better placed functions into files (spreadsheet creation files are now in ``spreadsheet.py``).
* Added a KiCost stamp version at the end of the spreadsheet and file information in the beginning, if they are not inside it.
* Fixed issues related to user visualization in the spreadsheet (added gray formatted conditioning and the "exclude desc and manf columns").
* Added "user errors" and software scape in the case of not recognized references characters given the message of how to solve.
* Support for multiple quantity for a single manufacture code (before just worked when using multiple/sub-parts).
* Fixed the Altium EDA module.
* Created a graphical user interface based on wxWidgets (the dependence is asked to be installed at the first use).
* Added the ``--user`` option allow to use just ``kicost --user -i %file`` and others parameters will be got by the last configuration in the graphical interface (that save the user configurations).
* Added automatic recognition of the files of each EDA tool (for the graphical interface).


0.1.42 (2017-12-07)
______________________

* Processing of CSV files containing part information is now supported.
* Added ``show_dist_list`` option to display the list of distributors from which part cost data is available.
* Added capability to process multiple XML and CSV files. 


0.1.41 (2017-11-16)
______________________

* Fixed exception caused by missing 'href' key in product links extracted by TME module.


0.1.40 (2017-11-02)
______________________

* Fixed exceptions caused by .xml files without a title block or part library section.


0.1.39 (2017-10-10)
______________________

* Part number separator characters can now be escaped with backslashes in case they are actually part of part numbers.


0.1.38 (2017-10-09)
______________________

* Fixed webscrape retry error in TME distributor module.


0.1.37 (2017-10-09)
______________________

* A part manf# field can now contain multiple subpart numbers. Each part number can be
  assigned a multiplier to indicate the quantity of the subpart needed for each part.
* Unit price cells for parts now show complete Qty/Price table as a cell comment.
* Part quantity cells are now color-coded to indicate parts with insufficient availability.
* Part quantity cells are now color-coded to indicate parts for which insufficient quantity has been ordered.
* Project name, company, and date are now shown in the spreadsheet.
* New distributor can now be added just by creating a submodule in ``distributors``.
* Added distributor TME.
* Added ``--retries`` option to set the number of attempts at loading a distributor webpage.
* Fixed problem where "kicost:dnp" field was not recognized.


0.1.36 (2017-08-14)
______________________

* Parts may now be assigned to a variant by giving them a ``variant`` field.
* Parts may now be assigned to multiple variants.
* Parts may be designated as "do not populate" by giving them a ``DNP`` field.
* DNP parts or parts not in the current variant will not appear in the cost spreadsheet.


0.1.35 (2017-04-24)
______________________

* Fixed bug in scraping RS website when a part search results in a list of matches instead of a single product page.


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

* Corrected entrypoint in ``__main__.py``.

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
