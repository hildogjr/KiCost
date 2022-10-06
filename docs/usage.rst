========
Usage
========

KiCost's main use is generating part-cost spreadsheets for
circuit boards developed with KiCad as follows:

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

Distributors stock code can be also used through the specific field name listed bellow and
they are prioritized to get the part information.

Digi-Key: digikey#         digikey_#    digikey-#    digikeypn#    digikey_pn#    digikey-pn#
          digikeypn        ...

          digikeyvendor#   ...

          digikeynum       ...

          digikeyvp#       ...

          digikeyvpn       ...

Mouser:   mouser# ....
...

Be careful if the part have a ``manf#`` or distributor code with the ``,``, ``;`` or ``\`` characters,
these have specific propose as shown in *Parts With Subparts*. They have to be preceded by ``\``,
example, for the ``NUP1301,215`` code, use ``NUP1301\,215``.

2. Output a BOM from your KiCad schematic. This will be an XML file such as ``schem.xml``.

3. Process the XML file with KiCost to create a part-cost spreadsheet named ``schem.xlsx`` like this::

     kicost -i schem.xml

4. Open the ``schem.xlsx`` spreadsheet using Microsoft Excel, LibreOffice Calc, or Google Sheets.
   Then enter the number of boards that you need to build and see
   the prices for the total board and individual parts when purchased from 
   several different distributors (KiCost currently supports Arrow, Digi-Key, Mouser, Newark, Farnell, RS and TME).
   All of the pricing information reflects the quantity discounts currently in effect at
   each distributor.
   The spreadsheet also shows the current inventory of each part from each distributor so you can tell
   if there's a problem finding something and an alternate part may be needed.

5. Enter the quantity of each part that you want to purchase from each distributor.
   Lists of part numbers and quantities will appear that you can cut-and-paste
   directly into the website ordering page of each distributor.

------------------------
Examples
------------------------

Most people just want some examples of using KiCost so they don't have to read a bunch
of documentation, so here they are!

To create a cost spreadsheet from an XML file exported from KiCad::

    kicost -i schem.xml

To create a cost spreadsheet from within KiCad, use the
``Tools`` => ``Generate Bill of Materials...`` menu item and then enter the
following in the `Command line` field::

    kicost -i %I

To create a cost spreadsheet direct from the KiCad using the user definitions (by graphical interface last runned):
To create a cost spreadsheet from within KiCad using the previous, use the
``Tools`` => ``Generate Bill of Materials...`` menu item and then enter the
following in the ``Command line`` field::

    kicost -i %I --user

To place the spreadsheet in a file with a different name than the XML file::

    kicost -i schem.xml -o new_file.xlsx

To overwrite an existing spreadsheet::

    kicost -i schem.xml -w

To get costs from only a few distributors::

    kicost -i schem.xml --include digikey mouser

To exclude one or more distributors from the cost spreadsheet::

    kicost -i schem.xml --exclude digikey farnell

To include parts that are only used in a particular variant of a design::

    kicost -i schem.xml --variant V1

To create a cost spreadsheet from a CSV file of part data::

    kicost -i schem.csv --eda_tool csv

To read and merge different projects BOMs, even those from different EDA tools::

    kicost -i bom1.xml bom2.xml bom3.csv --eda kicad altium csv

To access KiCost through a graphical user interface, just use the `kicost`
command without parameters.

.. image:: guide_screen.png

------------------------
Custom BOM list
------------------------

In addition to XML files output by EDA tools, KiCost also accepts CSV files
as a method for getting costs of preliminary designs or older projects.
The format of the CSV file is as follows:

1. A single column is interpreted as containing manufacturer part numbers.
2. Two columns are interpreted as the manufacturer's part number followed by the part reference (e.g., ``R4``).
3. Three columns are interpreted as the quantity followed by the part number and reference.

You can also arrange the columns arbitrarily by placing a header in the first line 
of the CSV file that labels the particular 
columns as manufacturer's part numbers (``manf#``), quantities (``qty``), and
part references (``refs``).

------------------------
Custom Part Data
------------------------

The price breaks on some parts can't be obtained automatically because:

* they're not offered by one of the distributors whose web pages KiCost can scrape/query, or
* they're custom parts.

For these parts, you can manually enter price information as follows:

#. Create a new field for the part named ``kicost:pricing`` in either the schematic or library.
#. For the field value, enter a semicolon-separated list of quantities and prices which
   are separated by colons like so::

      1:$1.50; 10:$1.00; 25:$0.90; 100:$0.75
      
   (You can put spaces and currency symbols in the field value. KiCost will
   strip everything except digits, decimal points, semicolons, and colons.
   Others currency are acepted by use of the standardize ISO 4217 alpha3 format,
   e.g. ``USD1.50``, ``EUR1.00``)
   
You can also enter a link to documentation for the part using a field named ``kicost:link``.
The value of this field will be a web address like::

    www.reallyweirdparts.com/products/weird_product.html
   
After KiCost is run, the price information and clickable link to documentation
for the part are shown in a section of the spreadsheet labeled **Local**.
If you want to associate the pricing, documentation link and/or available quantity
to a particular source or distributor, just place an extra label within the field
key to indicate the source like so::

    kicost:My_Weird_Parts:pricing
    kicost:My_Weird_Parts:link
    kicost:My_Weird_Parts:avail
    
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
but that shouldn't exclude the part from a group that has none or different notes.
There are three ways to prevent this:

#. Use the ``--ignore_fields`` command-line option to make KiCost ignore part fields
   with certain names::

     kicost -i schematic.xml --ignore_fields notes

#. Use the ``--group_fields`` option to allow grouping of parts even if they
   have different field values, but then display the parts separately in the
   spreadsheet using a multiline cell.
   The following example will group parts that are identical except for having
   different footprints, but will display them individually::

     kicost -i schematic.xml --group_fields footprint

#. Precede the field name with a ":" such as ``:note``. This makes KiCost ignore the
   field because it is in a different namespace.

------------------------
Parts With Subparts
------------------------

Some parts consist of two or more subparts.
For example, a two-pin jumper might have an associated shunt.
This is represented by placing the part number for each subpart into the ``manf#`` field, separated
by a "|" (ASCII 124) like so: ``JMP1A45|SH3QQ5``. The ``manf`` (manufacturer name) also allows this division.
You can leave a position empty or replicate the last one (use "~" character to replicate the last one).
Each subpart will be placed on a separate row of the spreadsheet with its associated part number
and a part reference created from the original part reference adding "#" and a number.
For example, if the two-pin jumper had a part reference of ``JP6``, then there
would be two rows in the spreadsheet containing data like this:

::

    JP6#1  ...  JMP1A45
    JP6#2  ...  SH3QQ5

You can also specify multipliers for each subpart by either prepending or appending
the subpart part number with a multiplier separated by a ":".
To illustrate, a 2x2 jumper paired with two shunts would have a part number of
``JMP2B26| SH3QQ5:2``.
The multiplier can be either an integer, float or fraction
and it can precede or follow the part code (e.g. ``SH3QQ5:2`` or ``2:SH3QQ5``).

In the case of ``distributor#`` and ``manf#`` for one sub part only, the other should have a blank
value discriminated. As example:

::

    manf#    =  0022232061|0022012067| 6: 08-50-0114|  LA 55-P| lv 25-P
    digikey# =  ||| 398-1010-ND| 398-1019-ND
    rs#      =  ||| 180-7357| 286-361

See that just the last two ``manf#`` have a corresponding ``digikey#`` and ``rs#`` catalogue code.

This mechanism is applied to the following fields: ``manf``, ``manf#`` and any ``DISTRIBUTOR#`` field.
A similar mechanism is applied to the ``pricing`` field, but the multiplier mechanism isn't applied.
If you want to process more fields add them using the ``--split_extra_fields`` option.

For compatibility with older versions of KiCost you can also use "," or ";" as separator for ``manf``,
``manf#`` and any ``DISTRIBUTOR#`` field.
    

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
to be omitted from the cost calculation spreadsheet. Note that empty strings will be
interpreted as zero (i.e. ``kicost.VARIANT:dnp=""`` and ``kicost.VARIANT:dnp=" "`` will
be interpreted as ``kicost.VARIANT:dnp="0"``)

-----------------------------------------------
Showing Extra Part Data in the Spreadsheet
-----------------------------------------------

Sometimes it is desirable to show additional data for the parts in the
spreadsheet.
To do this, use the ``--fields`` command-line option followed by the names of the
additional part fields you want displayed in the global data section of the
of the spreadsheet::

    kicost -i schematic.xml --fields fld1 fld2

--------------------------------
Visual Cues in the Spreadsheet
--------------------------------

In addition to the part cost information, the spreadsheet output by KiCost
provides additional cues:

#. The ``Manf#`` cell is colored to warning the part lifecyle status:

   * Purple if the part is asign as 'obsolete' or 'not recommended for new designs' by one of the distributors accessed.

#. The ``Qty`` cell is colored to show the availability of a given part:

   * Red if the part is unavailable at any of the distributors.
   * Orange if the part is available, but not in sufficient quantity.
   * Yellow if there is enough of the part available, but not enough has been ordered.
   * Gray if no manufacturer or distributor part number was found in the BOM file.

#. The ``Avail`` cell is colored to show the availability of a given part
   at a particular distributor:

   * Red if the part is unavailable.
   * Orange if there is not sufficient quantity of the part available.

#. The ``Purch`` cell is colored to check the user purchase cart validity:

   * Red if try to purchase more than avaliable part
   * Yellow if try to purchase less than the minimum order quantity

#. The ``Unit$`` and ``Ext$`` in each distributor cell is colored green
   to indicate the lowest price found across all the distributors.

--------------------------------------
Selecting Distributors to Scrape/Query
--------------------------------------

You can get the list of part distributors that KiCost scrapes/query for data like this::

    kicost --show_dist_list
    Distributor list: digikey farnell local_template mouser newark rs tme

Since you may not have access to some of the distributors in that list,
you can restrict scraping from only a subset of them as follows::

    kicost -i schem.xml --include digikey mouser

Or you can exclude some distributors require the price of the rest::

    kicost -i schem.xml --exclude farnell newark

---------------------
Command-Line Options
---------------------

::

 usage: kicost [-h] [-v] [--info] [-i FILE.XML [FILE.XML ...]] [-o [FILE.XLSX]]
               [-f NAME [NAME ...]] [--translate_fields NAME [NAME ...]]
               [--variant VARIANT [VARIANT ...]] [-w] [-q]
               [--ignore_fields NAME [NAME ...]]
               [--group_fields NAME [NAME ...]] [--debug [LEVEL]]
               [--eda {kicad,altium,csv} [{kicad,altium,csv} ...]]
               [--show_dist_list] [--show_eda_list] [--no_collapse]
               [--show_cat_url] [-e DIST [DIST ...]]
               [--include DIST [DIST ...]] [--no_price] [--currency [CURRENCY]]
               [--gui FILE.XML [FILE.XML ...]] [--user] [--setup] [--unsetup]
 
 
 Build cost spreadsheet for a KiCAD project.
 
 optional arguments:
   -h, --help            show this help message and exit
   -v, --version         show program's version number and exit
   --info                Show program' and library information and version.
   -i FILE.XML [FILE.XML ...], --input FILE.XML [FILE.XML ...]
                         One or more schematic BOM XML files.
   -o [FILE.XLSX], --output [FILE.XLSX]
                         Generated cost spreadsheet.
   -f NAME [NAME ...], --fields NAME [NAME ...]
                         Specify the names of additional part fields to extract
                         and insert in the global data section of the
                         spreadsheet.
   --translate_fields NAME [NAME ...]
                         Specify or remove field translation (--translate X1 Y1
                         X2 Y2 X3 ~, translates X1 to Y1 and X2 to Y2 and
                         remove X3 for the internal dictionary).
   --variant VARIANT [VARIANT ...]
                         schematic variant name filter using regular expression.
   -w, --overwrite       Allow overwriting of an existing spreadsheet.
   -q, --quiet           Enable quiet mode with no warnings.
   --ignore_fields NAME [NAME ...]
                         Declare part fields to ignore when reading the BoM
                         file.
   --group_fields NAME [NAME ...]
                         Declare part fields to merge when grouping parts.
   --debug [LEVEL]       Print debugging info. (Larger LEVEL means more info.)
   --eda {kicad,altium,csv} [{kicad,altium,csv} ...]
                         Choose EDA tool from which the XML BOM file
                         originated, or use csv for .CSV files.
   --show_dist_list      Show list of distributors that can be scraped for cost
                         data, then exit.
   --show_eda_list       Show list of EDA tools whose files KiCost can read,
                         then exit.
   --no_collapse         Do not collapse the part references in the
                         spreadsheet.
   --show_cat_url        Do not suppress the catalogue links into the catalogue
                         code in the spreadsheet.
   -e DIST [DIST ...], --exclude DIST [DIST ...]
                         Excludes the given distributor(s) from the scraping
                         process.
   --include DIST [DIST ...]
                         Includes only the given distributor(s) in the scraping
                         process.
   --no_price            Create a spreadsheet without scraping part data from
                         distributor websites.
   --currency [CURRENCY]
                         Define the priority currency. Use the ISO4217 for
                         currency (`USD`, `EUR`). Default: `USD`.
   --gui FILE.XML [FILE.XML ...]
                         Start the GUI to run KiCost passing the file parameter
                         give by "--input", all others parameters are ignored.
   --user                Run KiCost on terminal using the parameters in the GUI
                         memory, all passed parameters from terminal take
                         priority.
   --setup               Run KiCost integration (with KiCad and OS)
                         configuration script.
   --unsetup             Undo the KiCost integration.



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

#. If you have the GUIDE dependences insalled, it could be used::

      path_to_kicost --user -i "%1"

   So, KiCost will use the last preferences setted on the GUI to scrape/query, including
   which distributors to use, currency and others definitions.

#. Close the registry. KiCost should now appear when you right-click on an XML file.
