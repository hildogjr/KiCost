========
Usage
========

KiCost is mainly intended to be run as a script for generating part-cost spreadsheets for
circuit boards developed with KiCad. Typical use is as follows:

1. For each part in your schematic, create a field called ``manf#`` and set the field value
   to the manufacturer's part number.
   (You can reduce the effort of adding this information to individual parts by
   placing the ``manf#`` field into the part info in the schematic library so it gets applied globally.)
   The allowable field names for part numbers are::

        mpn          pn           p#
        part_num     part-num     part#
        manf_num     manf-num     manf#  
        man_num      man-num      man# 
        mfg_num      mfg-num      mfg#  
        mfr_num      mfr-num      mfr# 
        mnf_num      mnf-num      mnf# 

2. Output a BOM from your KiCad schematic. This will be an XML file such as ``schem.xml``.
3. Process the XML file with KiCost to create a part-cost spreadsheet named ``schem.xlsx`` like this::

     python kicost -i schem.xml

4. Open the ``schem.xlsx`` spreadsheet using Microsoft Excel, LibreOffice Calc, or Google Sheets.
   Then enter the number of boards that you need to build and see
   the prices for the total board and individual parts when purchased from 
   several different distributors (KiCost currently supports Digi-Key, Mouser, Newark, Farnell, RS and TME).
   All of the pricing information reflects the quantity discounts currently in effect at
   each distributor.
   The spreadsheet also shows the current inventory of each part from each distributor so you can tell
   if there's a problem finding something and an alternate part may be needed.
5. Enter the quantity of each part that you want to purchase from each distributor.
   Lists of part numbers and quantities will appear that you can cut-and-paste
   directly into the website ordering page of each distributor.

------------------------
Custom BOM list
------------------------

KiCost acept also CSV custom BOM list (also the format for some other EDA softwares). This is a way to get the up to date price of a hand made list or older projects. It is interpreted as CSV `,` `;` or `\t` (using multiple '\t' to align the columns) separeted format, even the number of columns is dinamic.

1. For just one column all lines are interpret as `manf#`;
2. For two `manf#` and `refs`;
3. For three `qty`, `manf#` and `refs`;
4. For more information is needed to use a CSV header in the first line of the file (the road map is interpret also if the firsts line have some prject information such as author or company, but not now).

Each of this columns can be ignored the module set the default value. E.g. to case 3 use `3,PART-CODE,` for one list without reference strings.

------------------------
Custom Part Data
------------------------

The price breaks on some parts can't be obtained automatically because:

* they're not offered by one of the distributors whose web pages KiCost can scrape, or
* they're custom parts.

For these parts, you can manually enter price information as follows:

#. Create a new field for the part named ``kicost:pricing`` in either the schematic or library.
#. For the field value, enter a semicolon-separated list of quantities and prices which
   are separated by colons like so::

      1:$1.50; 10:$1.00; 25:$0.90; 100:$0.75
      
   (You can put spaces and currency symbols in the field value. KiCost will
   strip everything except digits, decimal points, semicolons, and colons.)
   
You can also enter a link to documentation for the part using a field named ``kicost:link``.
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
* If two or more parts in the group have ``different`` data, then any parts without
  data are left that way because it is impossible to figure out which data should
  be propagated to them.

It is possible that there are identical parts in your schematic that have differing data
and, hence, wouldn't be grouped together.
For example, you might store information about a part in a "notes" field,
but that shouldn't exclude the part from a group that had none or different notes.
That can be prevented in two ways:

#. Use the ``-ignore_fields`` command-line option to make KiCost ignore part fields
   with certain names::

     kicost -i schematic.xml -ignore_fields notes

#. Precede the field name with a ":" such as ``:note``. This makes KiCost ignore the
   field because it is in a different namespace.

------------------------
Parts With Subparts
------------------------

Some parts consist of two or more subparts.
For example, a two-pin jumper might have an associated shunt.
This is represented by placing the part number for each subpart into the ``manf#`` field, separated
by a ";" like so: ``JMP1A45;SH3QQ5``. The ``manf`` (manufacture name) also allow this division, empty or replicate the last one (use "~" character to replicate the last one).
Each subpart will be placed on a separate row of the spreadsheet with its associated part number
and a part reference formed from the original part reference with an added "#" and a number. 
For example, if the two-pin jumper had a part reference of ``JP6``, then there
would be two rows in the spreadsheet containing data like this:

::

    JP6#1  ...  JMP1A45
    JP6#2  ...  SH3QQ5

You can also specify multipliers for each subpart by either prepending or appending
the subpart part number with a multiplier separated by a ":".
To illustrate, a 2x2 jumper paired with two shunts would have a part number of
``JMP2B26; SH3QQ5:2``.
The multiplier can be either an integer, float or fraction and it can be used
previous or succeding the part code, e.g. ``SH3QQ5:2`` or ``2:SH3QQ5``.

------------------------
Schematic Variants
------------------------

There are cases where a schematic needs to be priced differently depending
upon the context.
For example, the price of the end-user circuit board might be needed, but
then the price for the board plus additional parts for test also has to be 
calculated.

KiCost supports this using a ``variant`` field for parts in the schematic in
conjunction with the ``--variant`` command-line option.
Suppose a circuit has a connector, J1, that's only inserted for certain units.
If a field called ``variant`` is added to J1 and given the value V1,
then KiCost will ignore it during a normal cost calculation.
But J1 will be included in the cost calculation spreadsheet if you run KiCost like so::

    kicost -i schematic.xml --variant V1

In more complicated situations, you may have several circuit variants, some of which
are used in combination.
The ``--variant`` option will accept a regular expression as its argument
so, for example, you could get the cost of a board that includes circuitry for
both variants V1 and V2 with::

    kicost -i schematic.xml --variant "(V1|V2)"

A part can be a member of more than one variant by loading its ``variant`` field
with a list such as "V1, V2".
(The allowed delimiters for the list are comma (,), semicolon (;), slash (/), and space ( ).)
The part will be included in the cost calculation spreadsheet if any of its variants matches
the ``--variant`` argument.

..........................
Old-Style Variants
..........................

KiCost supports another way of specifying the variant associated with a part.
Using the example from above, labeling the part number for J1 as
``kicost.v1:manf#`` will assign it to the v1 variant.
This method is not as flexible as using the ``variant`` field and may be removed
in future versions of KiCost.

-----------------------------------------------
"Do Not Populate" Parts
-----------------------------------------------

Some parts in a schematic are not intended for insertion on the final board assembly.
These "do not populate" (DNP) parts can be assigned a field called ``DNP`` or ``NOPOP``.
Setting the value of this field to a non-zero number or any string will cause this part
to be omitted from the cost calculation spreadsheet.

-----------------------------------------------
Showing Extra Part Data in the Spreadsheet
-----------------------------------------------

Sometimes it is desirable to show additional data for the parts in the
spreadsheet.
To do this, use the ``-fields`` command-line option followed by the names of the
additional part fields you want displayed in the global data section of the
of the spreadsheet::

    kicost -i schematic.xml --fields fld1 fld2

--------------------------------
Visual Cues in the Spreadsheet
--------------------------------

In addition to the part cost information, the spreadsheet output by KiCost
provides additional cues:

#. The ``Qty`` cell is colored to show the availability of a given part:
       * Red if the part is unavailable at any of the distributors.
       * Orange if the part is available, but not in sufficient quantity.
       * Yellow if there is enough of th part available, but not enough has been ordered.
#. The ``Avail`` cell is colored to show the availability of a given part
   at a particular distributor:
       * Red if the part is unavailable.
       * Orange if there is not sufficient quantity of the part available.
#. The ``Unit$`` cell is colored green to indicate the lowest price found
   across all the distributors.

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

    usage: kicost [-h] [-v] [-i [files.xml]] [-o [file.xlsx]] [-f name [name ...]]
                  [-var [VARIANT]] [-w] [-s] [-q] [-np [NUM_PROCESSES]]
                  [-ign name [name ...]] [-d [LEVEL]] [--eda_tool {kicad,altium}]
                  [-e dist [dist ...]] [--include dist [dist ...]]
                  [--retries [num_retries]]

    Build cost spreadsheet for a KiCAD project.

    optional arguments:
      -h, --help            show this help message and exit
      -v, --version         show program's version number and exit
      -i [file1.xml file2.xml ...], --input [file1.xml file2.xml ...]
                            Schematic BOM XML file.
      -o [file.xlsx], --output [file.xlsx]
                            Generated cost spreadsheet. If not used is assumed the
                            same as the input file or combination of them.
      -f name [name ...], --fields name [name ...]
                            Specify the names of additional part fields to extract
                            and insert in the global data section of the
                            spreadsheet.
      -var [VARIANT1 VARIANT2 ...], --variant [VARIANT1 VARIANT2]
                            schematic variant name filter. VARIANT by file input
                            order, if used just one is assumed the same for all input
                            files.
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
      -eda {kicad,altium} [ead1 ead2 ...], --eda_tool {kicad,altium} [ead1 ead2 ...]
                            Choose EDA tool from which the .XML BOM file
                            originated, in the order of file input, if informat
                            just one, is assumed the same for all files.
      -e dist [dist ...], --exclude dist [dist ...]
                            Excludes the given distributor(s) from the scraping
                            process.
      --include dist [dist ...]
                            Includes only the given distributor(s) in the scraping
                            process.
      --rt [num_retries], --retries [num_retries]
                            Specify the number of attempts to retrieve part data
                            from a website.

----------------------------
Using KiCost direct in KiCad
----------------------------

In the Bill of Material window use the the command

    kicost - i %1 -w -q


-------------------------------------------------
Adding KiCost to the Context Menu (Windows Only)
-------------------------------------------------

You can add KiCost to the Windows context menu so you can right-click on an
XML file and generate the pricing spreadsheet.
To do this:

#. Open the registry and find the ``HKEY_CLASSES_ROOT => xmlfile => shell`` key. 
   Then add a ``KiCost`` key to it and, under that, add a ``command`` key.
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
