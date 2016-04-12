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

It is possible that there are identical parts in your schematic that have differing data
and, hence, wouldn't be grouped together.
For example, you might store information about a part in a "notes" field,
but that shouldn't exclude the part from a group that had no or different notes.
That can be prevented in two ways:

#. Use the ``-ignore_fields`` command-line option to make KiCost ignore part fields
   with certain names::

     kicost -i schematic.xml -ignore_fields notes

#. Precede the field name with a ":" such as ``:note``. This makes KiCost ignore the
   field because it is in a different namespace.

------------------------
Schematic Variants
------------------------

There are cases where a schematic might need to be priced differently depending
upon the context.
For example, the price of the end-user circuit board might be needed, but
then the price for the board plus additional parts for test also has to be 
calculated.

KiCost supports this with augmented the part field labels in the schematic in
conjunction with the ``--variant`` command-line option.
Suppose a circuit has a connector, J1, that's only inserted for certain units.
If the manufacturer's part number field for J1 is given the label ``kicost.v1:manf#``,
then KiCost will ignore it during a normal cost calculation.
But J1 will be included in the cost calculation if you run KiCost like so::

    kicost -i schematic.xml --variant v1

In more complicated situations, you may have several circuit variants, some of which
are combined in combination.
The ``--variant`` option will accept a regular expression as its argument
so, for example, you could get the cost of a board that includes circuitry for both variants 1
and 3 with::

    kicost -i schematic.xml --variant "(v1|v2)"

-----------------------------------------------
Showing Extra Part Data in the Spreadsheet
-----------------------------------------------

Sometimes it is desirable to show additional data for the parts in the
spreadsheet.
To do this, use the ``-fields`` command-line option followed by the names of the
additional part fields you want displayed in the global data section of the
of the spreadsheet:

    kicost -i schematic.xml --fields fld1 fld2

-----------------------
Parallel Web Scraping
-----------------------

KiCost spends most of its time scraping the part data from the distributor
web sites.
In order to speed this up, many of the web scrapes can be run in parallel.
By default, KiCost uses 30 parallel processes to gather the part data.
This can be too much for some computers, so you can decrease the load
using the ``--num_processes`` command-line option with the number of
processes you want to spawn::

    kicost -i schematic.xml -num_processes 10

In addition, you can use the ``--serial`` command-line option to force KiCost
into single-threaded operation.
This is equivalent to using ``-num_processes 1``.
(If you encounter problems running KiCost on a Windows PC with Python 2, then
using this command may help.)

---------------------
Command-Line Options
---------------------

::

usage: kicost [-h] [-v] [-i [file.xml]] [-o [file.xlsx]]
              [-f name [name ...]] [-var [VARIANT]] [-w] [-s] [-q]
              [-np [NUM_PROCESSES]] [-ign name [name ...]] [-d [LEVEL]]

Build cost spreadsheet for a KiCAD project.

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -i [file.xml], --input [file.xml]
                        Schematic BOM XML file.
  -o [file.xlsx], --output [file.xlsx]
                        Generated cost spreadsheet.
  -f name [name ...], --fields name [name ...]
                        Specify the names of additional part fields to extract
                        and insert in the global data section of the
                        spreadsheet.
  -var [VARIANT], --variant [VARIANT]
                        schematic variant name filter
  -w, --overwrite       Allow overwriting of an existing spreadsheet.
  -s, --serial          Do web scraping of part data using a single process.
  -q, --quiet           Enable quiet mode with no warnings.
  -np [NUM_PROCESSES], --num_processes [NUM_PROCESSES]
                        Set the number of parallel processes used for web
                        scraping part data.
  -ign name [name ...], --ignore_fields name [name ...]
                        Declare part fields to ignore when grouping parts.
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