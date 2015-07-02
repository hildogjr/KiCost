========
Usage
========

KiCost is mainly intended to be run as a script for generating part-cost spreadsheets for
circuit boards developed with KiCad. Typical use is as follows:

1. For each part in your schematic, create a field called `manf#` and set the field value
   to the manufacturer's part number. (You can reduce the effort of adding this information to individual parts by
   placing the `manf#` field and value into the part info in the schematic library so it gets applied globally.)
2. Output a BOM from your KiCad schematic. This will be an XML file. For this example, say it is `schem.xml`.
3. Process the XML file with KiCost to create a part-cost spreadsheet named `schem.xlsx` like this::

     python kicost -i schem.xml

4. Open the `schem.xlsx` spreadsheet using Microsoft Excel, LibreOffice Calc, or Google Sheets.
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
