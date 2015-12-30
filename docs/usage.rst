========
Usage
========

KiCost is mainly intended to be run as a script for generating part-cost spreadsheets for
circuit boards developed with KiCad. Typical use is as follows:

1. For each part in your schematic, create a field called *manf#* and set the field value
   to the manufacturer's part number. (You can reduce the effort of adding this information to individual parts by
   placing the *manf#* field into the part info in the schematic library so it gets applied globally.)
2. Output a BOM from your KiCad schematic. This will be an XML file. For this example, say it is *schem.xml*.
3. Process the XML file with KiCost to create a part-cost spreadsheet named *schem.xlsx* like this::

     python kicost -i schem.xml

4. Open the *schem.xlsx* spreadsheet using Microsoft Excel, LibreOffice Calc, or Google Sheets.
   Then enter the number of boards that you need to build and see
   the prices for the total board and individual parts when purchased from 
   several different distributors (KiCost currently supports Digi-Key, Mouser and Newark/Element14).
   All of the pricing information reflects the quantity discounts currently in effect at
   each distributor.
   The spreadsheet also shows the current inventory of each part from each distributor so you can tell
   if there's a problem finding something and an alternate part may be needed.
5. Enter the quantity of each part in your schematic that you want to purchase from each distributor.
   Lists of part numbers and quantities will appear in formats that you can cut-and-paste
   directly into the website ordering page of each distributor.

------------------------
Custom Part Data
------------------------

The price breaks on some parts can't be obtained automatically because:

* they're not offered by one of the distributors whose web pages KiCost can scrape, or
* they're custom parts.

For these parts, you can manually enter price information as follows:

#. Create a new field for the part named *kicost:pricing* in either the schematic or library.
#. For the field value, enter a semicolon-separated list of quantities and prices which
   are separated by colons like so::

      1:$1.50; 10:$1.00; 25:$0.90; 100:$0.75
      
   (You can put spaces and currency symbols in the field value. KiCost will
   strip everything except digits, decimal points, semicolons, and colons.)
   
You can also enter a link to documentation for the part using a field named *kicost:link*.
The value of this field will be a web address like::

    www.reallyweirdparts.com/products/weird_product.html
   
After KiCost is run, the price information and clickable link to documentation
for the part are shown in a section of the spreadsheet labeled **Local**.
If you want to associate the pricing and/or documentation link to a particular
source or distributor, just place an extra label within the field key to indicate
the source like so::

    kicost:My_Weird_Parts:pricing
    kicost:My_Weird_Parts:link
    
Then the pricing and documentation link for that part will appear in a section
of the spreadsheet labeled **My_Weird_Parts**.

You can have as many sources for parts as you want, and a part may have multiple sources.

------------------------
Part Grouping
------------------------

KiCost groups similar parts together and places their information on a single line
of the generated spreadsheet.
For parts to be grouped, they must:

* come from the same library (e.g., "device"),
* be the same part (e.g., "R"),
* have the same value (e.g., "10K" but note that this **would not match** "10000" or "10K0"), and
* have the same footprint (e.g., "Resistors_SMD:R_0805_HandSoldering").

To reduce your effort, KiCost will also propagate pricing data among grouped parts.
For example, if you place a hundred 0.1 uF decoupling capacitors in 0805 packages 
in a schematic, you need only assign a manufacturer's number and/or pricing data 
to one of them and it will be applied to the rest. 

There are several cases that are considered when propagating part data:

* If only one of the parts has data, that data is propagated to all the other parts
  in the group.
* If two or more parts have data but it is identical, then that
  data is propagated to any of the parts in the group without data.
* If two or more parts in the group have *different* data, then any parts without
  data are left that way because it is impossible to figure out which data should
  be propagated to them.

---------------------
Command-Line Options
---------------------

::

    usage: kicost [-h] [-v] [-i [file.xml]] [-o [file.xlsx]] [-w] [-s] [-d [LEVEL]]

    Build cost spreadsheet for a KiCAD project.

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit
      -i [file.xml], --input [file.xml]
                            Schematic BOM XML file.
      -o [file.xlsx], --output [file.xlsx]
                            Generated cost spreadsheet.
      -w, --overwrite       Allow overwriting of an existing spreadsheet.
      -s, --serial          Do web scraping of part data using a single process.
      -d [LEVEL], --debug [LEVEL]
                            Print debugging info. (Larger LEVEL means more info.)

-------------------------------------------------
Adding KiCost to the Context Menu (Windows Only)
-------------------------------------------------

You can add KiCost to the Windows context menu so you can right-click on an
XML file and generate the pricing spreadsheet.
To do this:

#. Open the registry and find the *HKEY_CLASSES_ROOT => xmlfile => shell* key. 
   Then add a *KiCost* key to it and, under that, add a *command* key.
   The resulting hierarchy of keys will look like this::

    HKEY_CLASSES_ROOT
            |
            +-- xmlfile
                  |
                  +-- shell
                        |
                        +-- KiCost
                              |
                              +-- command
                              
#. Set the value of the command to::

      path_to_kicost -w -i "%1"

   For example, the command value I use is::

      C:\winpython3\python-3.4.3\scripts\kicost -w -i "%1"

#. Close the registry. KiCost should now appear when you right-click on an XML file.