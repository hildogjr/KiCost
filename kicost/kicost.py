# MIT license
# 
# Copyright (C) 2015 by XESS Corporation
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import pprint
import re
import difflib
from bs4 import BeautifulSoup
import urllib as URLL
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range, xl_range_abs

__all__ = ['kicost']  # Only export this routine for use by the outside world.

THIS_MODULE = sys.modules[__name__]  # Reference to this module for making named calls.

# Global array of distributor names.
distributors = {
    'digikey': {
        'label': 'Digi-Key',
        'order_cols': ['purch', 'part_num', 'refs'],
        'order_delimiter': ','
    },
    'mouser': {
        'label': 'Mouser',
        'order_cols': ['part_num', 'purch', 'refs'],
        'order_delimiter': ' '
    },
    'newark': {
        'label': 'Newark',
        'order_cols': ['part_num', 'purch', 'refs'],
        'order_delimiter': ','
    }
}

dbg_level = None


def debug_print(level, msg):
    if dbg_level == None:
        return
    if level <= dbg_level:
        print msg
        
        
def kicost(in_file, out_filename, debug_level=None):
    '''Take a schematic input file and create an output file with a cost spreadsheet in xlsx format.'''

    global dbg_level
    dbg_level = debug_level

    # Get groups of identical parts.
    parts = get_part_groups(in_file)

    # Get the distributor product page for each part and parse it into a tree.
    debug_print(1, 'Get parsed product page for each component group...')
    for part in parts:
        part.html_trees, part.urls = get_part_html_trees(part)

    # Create the part pricing spreadsheet.
    create_spreadsheet(parts, out_filename)

    # Print component groups for debugging purposes.
    if 2 <= dbg_level:
        for part in parts:
            for f in dir(part):
                if f.startswith('__'):
                    continue
                elif f.startswith('html_trees'):
                    continue
                else:
                    print '{} = '.format(f),
                    pprint.pprint(part.__dict__[f])
            print
        
    
def get_part_groups(in_file):
    '''Get groups of identical parts from an XML file and return them as a dictionary.'''

    LIB_DELIMITER = ':'  # Delimiter between library and component name.

    # Read-in the schematic XML file to get a tree and get its root.
    debug_print(1, 'Get schematic XML...')
    root = BeautifulSoup(in_file)

    # Find the parts used from each library.
    debug_print(1, 'Get parts library...')
    libparts = {}
    for p in root.find('libparts').find_all('libpart'):

        # Get the values for the fields in each library part (if any).
        fields = {}  # Clear the field dict for this part.
        try:
            for f in p.find('fields').find_all('field'):
                # Store the name and value for each field.
                fields[f['name'].lower()] = f.string
        except AttributeError:
            # No fields found for this part.
            pass

        # Store the field dict under the key made from the
        # concatenation of the library and part names.
        libparts[p['lib'] + LIB_DELIMITER + p['part']] = fields

        # Also have to store the fields under any part aliases.
        try:
            for alias in p.find('aliases').find_all('alias'):
                libparts[p['lib'] + LIB_DELIMITER + alias.string] = fields
        except AttributeError:
            pass  # No aliases for this part.

    # Find the components used in the schematic and elaborate
    # them with global values from the libraries and local values
    # from the schematic.
    debug_print(1, 'Get components...')
    components = {}
    for c in root.find('components').find_all('comp'):

        # Find the library used for this component.
        libsource = c.find('libsource')

        # Create the key to look up the part in the libparts dict.
        libpart = libsource['lib'] + LIB_DELIMITER + libsource['part']

        # Initialize the fields from the global values in the libparts dict entry.
        # (These will get overwritten by any local values down below.)
        fields = libparts[libpart].copy()  # Make a copy! Don't use reference!

        # Store the part key and its value.
        fields['libpart'] = libpart
        fields['value'] = c.find('value').string

        # Get the footprint for the part (if any) from the schematic.
        try:
            fields['footprint'] = c.find('footprint').string
        except AttributeError:
            pass

        # Get the values for any other the fields in the part (if any) from the schematic.
        try:
            for f in c.find('fields').find_all('field'):
                fields[f['name'].lower()] = f.string
        except AttributeError:
            pass

        # Store the fields for the part using the reference identifier as the key.
        ref = c['ref']
        components[c['ref']] = fields

    # Get groups of identical components.
    debug_print(1, 'Get groups of identical components...')
    component_groups = {}
    for c in components:

        # Take the field keys and values of each part and create a hash.
        # Use the hash as the key to a dictionary that stores lists of
        # part references that have identical field values.
        h = hash(tuple(sorted(components[c].items())))

        # Now add the hashed component to the group with the matching hash
        # or create a new group if the hash hasn't been seen before.
        try:
            # Add next ref for identical part to the list.
            # No need to add field values since they are the same as the 
            # starting ref field values.
            component_groups[h].refs.append(c)
        except KeyError:

            class IdenticalComponents:
                pass  # Just need a temporary class here.

            component_groups[h] = IdenticalComponents()  # Add empty structure.
            component_groups[h].refs = [c]  # Init list of refs with first ref.
            component_groups[h].fields = components[c]  # Store field values.
            
    return component_groups.values()
    

def create_spreadsheet(parts, spreadsheet_filename):
    '''Create a spreadsheet using the info for the parts (including their HTML trees).'''

    DEFAULT_BUILD_QTY = 100  # Default value for number of boards to build.
    WORKSHEET_NAME = 'KiCost'  # Default name for part-pricing worksheet.

    # Create spreadsheet file.
    with xlsxwriter.Workbook(spreadsheet_filename) as workbook:

        # Create the various format styles used by various spreadsheet items.
        wrk_formats = {
            'global' : workbook.add_format({
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#303030'
            }),
            'digikey' : workbook.add_format({
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#CC0000'  # Digi-Key red.
            }),
            'mouser' : workbook.add_format({
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#004A85'  # Mouser blue.
            }),
            'newark' : workbook.add_format({
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#A2AE06'  # Newark/E14 olive green.
            }),
            'header' : workbook.add_format({
                'font_size': 12,
                'bold': True,
                'align': 'center',
                'valign': 'top',
                'text_wrap': True
            }),
            'board_qty' : workbook.add_format({
                'font_size': 13,
                'bold': True,
                'align': 'right'
            }),
            'total_cost_label' : workbook.add_format({
                'font_size': 13,
                'bold': True,
                'align': 'right',
                'valign': 'vcenter'
            }),
            'total_cost_currency' : workbook.add_format({
                'font_size': 13,
                'font_color': 'red',
                'bold': True,
                'num_format': '$#,##0.00',
                'valign': 'vcenter',
            }),
            'currency' : workbook.add_format({
                'num_format': '$#,##0.00'
            }),
            'centered_text' : workbook.add_format({
                'align': 'center'
            }),
        }

        # Create the worksheet that holds the pricing information.
        wks = workbook.add_worksheet(WORKSHEET_NAME)

        # Set the row & column for entering the part information in the sheet.
        START_COL = 0
        BOARD_QTY_ROW = 0
        TOTAL_COST_ROW = BOARD_QTY_ROW + 1
        START_ROW = 3
        LABEL_ROW = START_ROW + 1
        COL_HDR_ROW = LABEL_ROW + 1
        FIRST_PART_ROW = COL_HDR_ROW + 1
        LAST_PART_ROW = COL_HDR_ROW + len(parts) - 1

        # Load the global part information (not distributor-specific) into the sheet.
        # (next_col = the column immediately to the right of the global data.)
        next_col = add_globals_to_worksheet(wks, wrk_formats, START_ROW,
                                            START_COL,
                                            parts)
        # Create a defined range for the global data.
        workbook.define_name('global_part_data',
                             '={wks_name}!{data_range}'.format(
                                 wks_name=WORKSHEET_NAME,
                                 data_range=xl_range(START_ROW, START_COL,
                                                     LAST_PART_ROW, next_col - 1)))

        # Create the cell where the quantity of boards to assemble is entered.
        # Place the board qty cells near the right side of the global info.
        wks.write(BOARD_QTY_ROW, next_col - 2, 'Board Qty:',
                  wrk_formats['board_qty'])
        wks.write(BOARD_QTY_ROW, next_col - 1, DEFAULT_BUILD_QTY,
                  wrk_formats['board_qty']
                  )  # Set initial board quantity.
        # Define the named cell where the total board quantity can be found.
        workbook.define_name('BoardQty', '={wks_name}!{cell_ref}'.format(
            wks_name=WORKSHEET_NAME,
            cell_ref=xl_rowcol_to_cell(BOARD_QTY_ROW, next_col - 1,
                                       row_abs=True,
                                       col_abs=True)))

        # Create the row to show total cost of board parts for each distributor.
        wks.write(TOTAL_COST_ROW, next_col - 2, 'Total Cost:',
                  wrk_formats['total_cost_label'])

        # Freeze view of the global information and the column headers, but
        # allow the distributor-specific part info to scroll.
        wks.freeze_panes(COL_HDR_ROW, next_col)

        # Load the part information from each distributor into the sheet.
        for dist in distributors.keys():
            dist_start_col = next_col
            next_col = add_dist_to_worksheet(wks, wrk_formats, START_ROW,
                                             dist_start_col, TOTAL_COST_ROW, dist,
                                             parts)
            # Create a defined range for each set of distributor part data.
            workbook.define_name(
                '{}_part_data'.format(dist), '={wks_name}!{data_range}'.format(
                    wks_name=WORKSHEET_NAME,
                    data_range=xl_range(START_ROW, dist_start_col, LAST_PART_ROW,
                                        next_col - 1)))


def collapse_refs(refs):
    '''Collapse list of part references into a sorted, comma-separated list of hyphenated ranges.'''
    
    def convert_to_ranges(nums):
        '''Collapse a list of numbers into sorted, comma-separated, hyphenated ranges.
           e.g.: 3,4,7,8,9,10,11,13,14 => 3,4,7-11,13,14'''
        nums.sort()  # Sort all the numbers.
        num_ranges = [] # No ranges found yet since we just started.
        range_start = 0  # First possible range is at the start of the list of numbers.
        # Go through the list of numbers looking for 3 or more sequential numbers.
        while range_start < len(nums):
            num_range = nums[range_start] # Current range starts off as a single number.
            next_range_start = range_start + 1 # The next possible start of a range.
            # Look for sequences of three or more sequential numbers.
            for range_end in range(range_start + 2, len(nums)):
                if range_end - range_start != nums[range_end] - nums[range_start]:
                    break  # Non-sequential numbers found, so break out of loop.
                # Otherwise, extend the current range.
                num_range = [nums[range_start], nums[range_end]]
                # 3 or more sequential numbers found, so next possible range must start after this one.
                next_range_start = range_end + 1
            # Append the range (or single number) just found to the list of range.
            num_ranges.append(num_range)
            # Point to the start of the next possible range and keep looking.
            range_start = next_range_start
        return num_ranges

    # Regular expression for detecting part references consisting of a
    # prefix of non-digits followed by a sequence of digits, such as 'LED10'.
    ref_re = re.compile('(?P<prefix>\D+)(?P<num>\d+)', re.IGNORECASE)
    
    prefix_nums = {} # Contains a list of numbers for each distinct prefix.
    for ref in refs:
        # Partition each part reference into its beginning part prefix and ending number.
        match = re.search(ref_re, ref)
        prefix = match.group('prefix')
        num = int(match.group('num'))
        
        # Append the number to the list of numbers for this prefix, or create a list
        # with a single number if this is the first time a particular prefix was encountered.
        try:
            prefix_nums[prefix].append(num)
        except KeyError:
            prefix_nums[prefix] = [num]
            
    # Convert the list of numbers for each prefix into ranges.
    for prefix in prefix_nums.keys():
        prefix_nums[prefix] = convert_to_ranges(prefix_nums[prefix])
        
    # Combine the prefixes and number ranges back into part references.
    collapsed_refs = []
    for prefix, nums in prefix_nums.items():
        for num in nums:
            if type(num) == list:
                # Convert a range list into a collapsed part reference:
                # e.g., 'R10-R15' from 'R':[10,15].
                collapsed_refs.append('{0}{1}-{0}{2}'.format(prefix, num[0], num[-1]))
            elif type(num) == int:
                # Convert a single number into a simple part reference: e.g., 'R10'.
                collapsed_refs.append('{}{}'.format(prefix, num))
            else:
                raise Exception('Unknown part reference {}{}'.format(prefix,num))
                
    # Return the collapsed par references.
    return collapsed_refs


def add_globals_to_worksheet(wks, wrk_formats, start_row, start_col, parts):
    '''Add global part data to the spreadsheet.'''
    
    # Columns for the various types of global part data.
    columns = {
        'refs': {
            'col': 0,
            'label': 'Refs',
            'comment': 'Schematic identifier for each part.'
        },
        'value': {
            'col': 1,
            'label': 'Value',
            'comment': 'Value of each part.'
        },
        'desc': {
            'col': 2,
            'label': 'Desc',
            'comment': 'Description of each part.'
        },
        'footprint': {
            'col': 3,
            'label': 'Footprint',
            'comment': 'PCB footprint for each part.'
        },
        'manf': {
            'col': 4,
            'label': 'Manf',
            'comment': 'Manufacturer of each part.'
        },
        'manf#': {
            'col': 5,
            'label': 'Manf#',
            'comment': 'Manufacturer number for each part.'
        },
        'qty': {
            'col': 6,
            'label': 'Qty',
            'comment': 'Total number of each part needed to assemble the board.'
        },
        # 'short': {
        # 'col': 7,
        # 'label': 'Short',
        # 'comment': 'Shortage of each part needed for assembly.'},
    }
    num_cols = len(columns.keys())
    
    row = start_row  # Start building global section at this row.

    # Add label for global section.
    wks.merge_range(row, start_col, row, start_col + num_cols - 1,
                    "Global Part Info", wrk_formats['global'])
    row += 1 # Go to next row.

    # Add column headers.
    for k in columns.keys():
        col = start_col + columns[k]['col']
        wks.write_string(row, col, columns[k]['label'], wrk_formats['header'])
        wks.write_comment(row, col, columns[k]['comment'])
    row += 1 # Go to next row.

    # Add global data for each part.
    for part in parts:

        # Enter part references.
        wks.write_string(row, start_col + columns['refs']['col'],
                         ','.join(collapse_refs(part.refs)))

        # Enter more data for the part.
        for field in ('value', 'desc', 'footprint', 'manf', 'manf#'):
            try:
                wks.write_string(row, start_col + columns[field]['col'],
                                 part.fields[field])
            except KeyError:
                pass

        # Enter total part quantity needed.
        try:
            wks.write(row, start_col + columns['qty']['col'],
                      '=BoardQty*{}'.format(len(part.refs)))
        except KeyError:
            pass

        # Enter part shortage quantity.
        try:
            wks.write(row, start_col + columns['short']['col'],
                      0)  # slack quantity. (Not handled, yet.)
        except KeyError:
            pass

        row += 1 # Go to next row.

    # Return column following the globals so we know where to start next set of cells.
    return start_col + num_cols


def add_dist_to_worksheet(wks, wrk_formats, start_row, start_col,
                          total_cost_row, dist, parts):
    '''Add distributor-specific part data to the spreadsheet.'''

    # Columns for the various types of distributor-specific part data.
    columns = {
        'avail': {
            'col': 0, # column offset within this distributor range of the worksheet.
            'level': 1, # Outline level (or hierarchy level) for this column.
            'label': 'Avail', # Column header label.
            'width': None, # Column width (default in this case).
            'comment': 'Available quantity of each part at the distributor.' # Column header tool-tip.
        },
        'purch': {
            'col': 1,
            'level': 2,
            'label': 'Purch',
            'width': None,
            'comment': 'Purchase quantity of each part from this distributor.'
        },
        'unit_price': {
            'col': 2,
            'level': 2,
            'label': 'Unit$',
            'width': None,
            'comment': 'Unit price of each part from this distributor.'
        },
        'ext_price': {
            'col': 3,
            'level': 0,
            'label': 'Ext$',
            'width': 15,  # Displays up to $9,999,999.99 without "###".
            'comment':
            '(Unit Price) x (Purchase Qty) of each part from this distributor.'
        },
        'part_num': {
            'col': 4,
            'level': 2,
            'label': 'Cat#',
            'width': None,
            'comment': 'Distributor-assigned part number for each part.'
        },
        'part_url': {
            'col': 5,
            'level': 2,
            'label': 'Doc',
            'width': None,
            'comment': 'Link to distributor webpage for each part.'
        },
    }
    num_cols = len(columns.keys())

    row = start_row  # Start building distributor section at this row.

    # Add label for this distributor.
    wks.merge_range(row, start_col, row, start_col + num_cols - 1,
                    distributors[dist]['label'], wrk_formats[dist])
    row += 1 # Go to next row.

    # Add column headers, comments, and outline level (for hierarchy).
    for k in columns.keys():
        col = start_col + columns[k]['col'] # Column index for this column.
        wks.write_string(row, col, columns[k]['label'], wrk_formats['header'])
        wks.write_comment(row, col, columns[k]['comment'])
        wks.set_column(col, col, columns[k]['width'], None,
                       {'level': columns[k]['level']})
    row += 1 # Go to next row.

    num_parts = len(parts)

    # Add distributor data for each part.
    PART_INFO_FIRST_ROW = row  # Starting row of part info.
    PART_INFO_LAST_ROW = PART_INFO_FIRST_ROW + num_parts - 1  # Last row of part info.
    
    # Get function names for getting data from the HTML tree for this distributor.
    get_dist_part_num = getattr(THIS_MODULE, 'get_{}_part_num'.format(dist))
    get_dist_qty_avail = getattr(THIS_MODULE, 'get_{}_qty_avail'.format(dist))
    get_dist_price_tiers = getattr(THIS_MODULE, 'get_{}_price_tiers'.format(dist))
    
    for part in parts:

        # Get the distributor part number from the HTML tree.
        dist_part_num = get_dist_part_num(part.html_trees[dist])
        
        # If the part number doesn't exist, the distributor doesn't stock this part
        # so leave this row blank.
        if len(dist_part_num) == 0:
            row += 1 # Skip this row and go to the next.
            continue
        
        # Enter distributor part number for ordering purposes.
        wks.write(row, start_col + columns['part_num']['col'], dist_part_num, None)

        # Enter quantity of part available at this distributor.
        wks.write(row, start_col + columns['avail']['col'],
                  get_dist_qty_avail(part.html_trees[dist]), None)

        # Purchase quantity always starts as blank because nothing has been purchased yet.
        wks.write(row, start_col + columns['purch']['col'], '', None)

        # Extract price tiers from distributor HTML page tree.
        price_tiers = get_dist_price_tiers(part.html_trees[dist])
        # Add the price for a single unit if it doesn't already exist in the tiers.
        try:
            min_qty = min(price_tiers.keys())
            if min_qty > 1:
                price_tiers[1] = price_tiers[
                    min_qty
                ]  # Set unit price to price of lowest available quantity.
        except ValueError:  # This happens if the price tier list is empty.
            pass
        price_tiers[0] = 0.00  # Enter quantity-zero pricing so LOOKUP works correctly in the spreadsheet.

        # Sort the tiers based on quantities and turn them into lists of strings.
        qtys = sorted(price_tiers.keys())
        prices = [str(price_tiers[q]) for q in qtys]
        qtys = [str(q) for q in qtys]

        needed_qty_col = 6  # TODO: Hard-coded column in the global table where part quantity is stored. Not good!
        purch_qty_col = start_col + columns['purch']['col']
        unit_price_col = start_col + columns['unit_price']['col']
        
        # Enter a spreadsheet lookup function that determines the unit price based on the needed quantity
        # or the purchased quantity (if that is non-zero), but only if the part number exists.
        wks.write_formula(
            row, unit_price_col,
            '=iferror(lookup(if({purch_qty}="",{needed_qty},{purch_qty}),{{{qtys}}},{{{prices}}}),"")'.format(
                needed_qty=xl_rowcol_to_cell(row, needed_qty_col),
                purch_qty=xl_rowcol_to_cell(row, purch_qty_col),
                qtys=','.join(qtys),
                prices=','.join(prices)), wrk_formats['currency'])

        # Enter the formula for the extended price = purch qty * unit price.
        wks.write_formula(
            row, start_col + columns['ext_price']['col'],
            '=iferror(if({purch_qty}="",{needed_qty},{purch_qty})*{unit_price},"")'.format(
                needed_qty=xl_rowcol_to_cell(row, needed_qty_col),
                purch_qty=xl_rowcol_to_cell(row, purch_qty_col),
                unit_price=xl_rowcol_to_cell(row, unit_price_col)),
            wrk_formats['currency'])

        # Enter a link to the distributor webpage for this part.
        wks.write_url(row, start_col + columns['part_url']['col'],
                      part.urls[dist], wrk_formats['centered_text'],
                      string='Link')

        # Finished processing distributor data for this part.              
        row += 1 # Go to next row.

    # Sum the extended prices for all the parts to get the total cost from this distributor.
    total_cost_col = start_col + columns['ext_price']['col']
    wks.write(total_cost_row, total_cost_col, '=sum({sum_range})'.format(
        sum_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                           PART_INFO_LAST_ROW, total_cost_col)),
              wrk_formats['total_cost_currency'])

    # Add list of part numbers and purchase quantities for ordering from this distributor.
    ORDER_FIRST_ROW = PART_INFO_LAST_ROW + 2
    ORDER_LAST_ROW = ORDER_FIRST_ROW + num_parts - 1

    order_col = {}
    order_col_numeric = {}
    order_delimiter = {}
    dist_col = {}
    for position, c in enumerate(distributors[dist]['order_cols']):
        order_col[c] = start_col + 1 + position
        order_col_numeric[c] = (c == 'purch')
        order_delimiter[c] = distributors[dist]['order_delimiter']
        if position + 1 == len(distributors[dist]['order_cols']):
            order_delimiter[c] = ''
        try:
            dist_col[c] = start_col + columns[c]['col']
        except KeyError:
            dist_col[c] = 0  # TODO: Hard-coded column in the global table where part refs are stored. Not good!

    def enter_order_info(info_col, order_col, numeric=False, delimiter=''):
        formula = '''
            IFERROR(
                CONCATENATE(
                    {num_to_text_func}(
                        INDEX(
                            {get_range},
                            SMALL(
                                IF(
                                    {sel_range1} <> "",
                                    IF(
                                        {sel_range2} <> "",
                                        ROW({sel_range1}) - MIN(ROW({sel_range1})) + 1,
                                        ""
                                    ),
                                    ""
                                ),
                                ROW()-ROW({ORDER_FIRST_ROW})+1
                            )
                        )
                        {num_to_text_fmt}
                    ),
                    {delimiter}
                ),
                ""
            )
        '''

        formula = re.sub('[\s\n]', '', formula)

        if numeric:
            num_to_text_func = 'TEXT'
            num_to_text_fmt = ',"##0"'
        else:
            num_to_text_func = ''
            num_to_text_fmt = ''

        if delimiter != '':
            delimiter = '"{}"'.format(delimiter)

        purch_qty_col = start_col + columns['purch']['col']
        part_num_col = start_col + columns['part_num']['col']

        for r in range(ORDER_FIRST_ROW, ORDER_LAST_ROW + 1):
            wks.write_array_formula(
                xl_range(r, order_col, r, order_col),
                '{{={formula}}}'.format(formula=formula.format(
                    ORDER_FIRST_ROW=xl_rowcol_to_cell(ORDER_FIRST_ROW, 0,
                                                      row_abs=True),
                    sel_range1=xl_range_abs(PART_INFO_FIRST_ROW, purch_qty_col,
                                            PART_INFO_LAST_ROW, purch_qty_col),
                    sel_range2=xl_range_abs(PART_INFO_FIRST_ROW, part_num_col,
                                            PART_INFO_LAST_ROW, part_num_col),
                    get_range=xl_range_abs(PART_INFO_FIRST_ROW, info_col,
                                           PART_INFO_LAST_ROW, info_col),
                    delimiter=delimiter,
                    num_to_text_func=num_to_text_func,
                    num_to_text_fmt=num_to_text_fmt)))

    for c in ('purch', 'part_num', 'refs'):
        enter_order_info(dist_col[c], order_col[c],
                         numeric=order_col_numeric[c],
                         delimiter=order_delimiter[c])

    return start_col + num_cols  # Return column following the globals so we know where to start next set of cells.


def get_digikey_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Digikey product page.'''
    price_tiers = {}
    try:
        for tr in html_tree.find('table', id='pricing').find_all('tr'):
            try:
                td = tr.find_all('td')
                qty = int(re.sub('[^0-9]', '', td[0].text))
                price_tiers[qty] = float(re.sub('[^0-9\.]', '', td[1].text))
            except IndexError:  # Happens when there's no <td> in table row.
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        return price_tiers  # Return empty price tiers.
    return price_tiers


def get_mouser_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Mouser product page.'''
    price_tiers = {}
    try:
        for tr in html_tree.find('table', class_='PriceBreaks').find_all('tr'):
            try:
                qty = int(re.sub('[^0-9]', '',
                                 tr.find('td',
                                         class_='PriceBreakQuantity').a.text))
                unit_price = tr.find('td', class_='PriceBreakPrice').span.text
                price_tiers[qty] = float(re.sub('[^0-9\.]', '', unit_price))
            except (TypeError, AttributeError, ValueError):
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        return price_tiers  # Return empty price tiers.
    return price_tiers


def get_newark_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Mouser product page.'''
    price_tiers = {}
    try:
        qty_strs = []
        for qty in html_tree.find(
            'table',
            class_=('tableProductDetailPrice', 'pricing')).find_all(
                'td',
                class_='qty'):
            qty_strs.append(qty.text)
        price_strs = []
        for price in html_tree.find(
            'table',
            class_=('tableProductDetailPrice', 'pricing')).find_all(
                'td',
                class_='threeColTd'):
            price_strs.append(price.text)
        qtys_prices = zip(qty_strs, price_strs)
        for qty_str, price_str in qtys_prices:
            try:
                qty = re.search('(\s*)([0-9,]+)', qty_str).group(2)
                qty = int(re.sub('[^0-9]', '', qty))
                price_tiers[qty] = float(re.sub('[^0-9\.]', '', price_str))
            except (TypeError, AttributeError, ValueError):
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        return price_tiers  # Return empty price tiers.
    return price_tiers


def digikey_part_is_reeled(html_tree):
    '''Returns True is this Digi-Key part is reeled or Digi-reeled.'''
    qty_tiers = get_digikey_price_tiers(html_tree).keys()
    if min(qty_tiers) >= 100:
        return True
    if html_tree.find('table',
                      class_='product-details-reel-pricing') is not None:
        return True
    return False


def get_digikey_part_num(html_tree):
    try:
        return re.sub('\n', '', html_tree.find('td',
                                               id='reportpartnumber').text)
    except AttributeError:
        return ''


def get_mouser_part_num(html_tree):
    try:
        return re.sub('\n', '', html_tree.find('div',
                                               id='divMouserPartNum').text)
    except AttributeError:
        return ''


def get_newark_part_num(html_tree):
    try:
        part_num_str = html_tree.find('div',
                                      id='productDescription').find(
                                          'ul').find_all('li')[1].text
        part_num_str = re.search('(Newark Part No.:)(\s*)([^\s]*)',
                                 part_num_str, re.IGNORECASE).group(3)
        return part_num_str
    except AttributeError:
        return ''


def get_digikey_qty_avail(html_tree):
    try:
        qty_str = html_tree.find('td', id='quantityavailable').text
    except AttributeError:
        return ''
    try:
        qty_str = re.search('(stock:\s*)([0-9,]*)', qty_str,
                            re.IGNORECASE).group(2)
        return int(re.sub('[^0-9]', '', qty_str))
    except (AttributeError, ValueError):
        return 0


def get_mouser_qty_avail(html_tree):
    try:
        qty_str = html_tree.find(
            'table',
            id='ctl00_ContentMain_availability_tbl1').find_all('td')[0].text
    except AttributeError:
        return ''
    try:
        return int(re.sub('[^0-9]', '', qty_str))
    except ValueError:
        return 0


def get_newark_qty_avail(html_tree):
    try:
        qty_str = html_tree.find('div',
                                 id='priceWrap').find(
                                     'div',
                                     class_='highLightBox').p.text
    except (AttributeError, ValueError):
        return ''
    try:
        return int(re.sub('[^0-9]', '', qty_str))
    except ValueError:
        return 0


def get_part_html_trees(part):
    '''Get the parsed HTML trees from each distributor website for the given part.'''
    html_trees = {}
    urls = {}
    fields = part.fields
    for dist in distributors.keys():
        debug_print(2, '{} {}'.format(dist, part.refs))
        get_dist_part_html_tree = getattr(THIS_MODULE,
                                          'get_{}_part_html_tree'.format(dist))
        try:
            if dist + '#' in fields:
                html_trees[dist], urls[dist] = get_dist_part_html_tree(
                    fields[dist + '#'])
            elif 'manf#' in fields:
                html_trees[dist], urls[dist] = get_dist_part_html_tree(
                    fields['manf#'])
            else:
                raise PartHtmlError
        except PartHtmlError, AttributeError:
            html_trees[dist] = BeautifulSoup('<html></html>')
            urls[dist] = ''
    return html_trees, urls


class FakeBrowser(URLL.FancyURLopener):
    ''' This is a fake browser string so the distributor websites will talk to us.'''
    version = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.124 Safari/537.36'


class PartHtmlError(Exception):
    '''Exception for failed retrieval of an HTML parse tree for a part.'''
    pass


def merge_digikey_price_tiers(main_tree, alt_tree):
    '''Merge the price tiers from the alternate-packaging tree into the main tree.'''
    try:
        insertion_point = main_tree.find('table', id='pricing').find('tr')
        for tr in alt_tree.find('table', id='pricing').find_all('tr'):
            insertion_point.insert_after(tr)
    except AttributeError:
        pass


def merge_digikey_qty_avail(main_tree, alt_tree):
    try:
        main_qty = get_digikey_qty_avail(main_tree)
        alt_qty = get_digikey_qty_avail(alt_tree)
        merged_qty = max(main_qty, alt_qty)
        insertion_point = main_tree.find('td', id='quantityavailable')
        insertion_point.string = 'Digi-Key Stock: {}'.format(merged_qty)
    except AttributeError:
        pass


def get_digikey_part_html_tree(pn, url=None, descend=2):
    '''Find the Digikey HTML page for a part number and return the URL and parse tree.'''
    #url='https://www.google.com/search?q=pic18f14k50-I%2FSS-ND+site%3Adigikey.com'
    #url = 'http://www.digikey.com/product-search/en?WT.z_homepage_link=hp_go_button&lang=en&site=us&keywords=' + URLL.quote(pn,safe='')
    #url = 'http://www.digikey.com/product-detail/en/PIC18F14K50T-I%2FSS/PIC18F14K50T-I%2FSSCT-ND/5013555'

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://www.digikey.com/scripts/DkSearch/dksus.dll?WT.z_header=search_go&lang=en&keywords=' + URLL.quote(
            pn,
            safe='')
    elif url[0] == '/':
        url = 'http://www.digikey.com' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    url_opener = FakeBrowser()
    html = url_opener.open(url).read()
    tree = BeautifulSoup(html)

    # If the tree contains the tag for a product page, then return it.
    if tree.find('html', class_='rd-product-details-page') is not None:

        # Digikey separates cut-tape and reel packaging, so we need to examine more pages 
        # to get all the pricing info. But don't descend any further if limit has been reached.
        if descend > 0:
            try:
                # Find all the URLs to alternate-packaging pages for this part.
                ap_urls = [
                    ap.find('td',
                            class_='lnkAltPack').a['href']
                    for ap in tree.find(
                        'table',
                        class_='product-details-alternate-packaging').find_all(
                            'tr',
                            class_='more-expander-item')
                ]

                ap_trees_and_urls = [get_digikey_part_html_tree(pn, ap_url,
                                                                descend=0)
                                     for ap_url in ap_urls]
                ap_trees_and_urls.append((tree, url))
                if digikey_part_is_reeled(tree):
                    for ap_tree, ap_url in ap_trees_and_urls:
                        if not digikey_part_is_reeled(ap_tree):
                            tree = ap_tree
                            url = ap_url
                            break

                for ap_tree, ap_url in ap_trees_and_urls:
                    if ap_tree is tree:
                        continue
                    try:
                        # Merge the pricing info from that into the main parse tree to make
                        # a single, unified set of price tiers...
                        merge_digikey_price_tiers(tree, ap_tree)
                        # and merge available quantity, using the maximum found.
                        merge_digikey_qty_avail(tree, ap_tree)
                    except AttributeError:
                        continue
            except AttributeError:
                pass
        return tree, url  # Return the parse tree and the URL where it came from.

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('html', class_='rd-product-category-page') is not None:
        if descend <= 0:
            raise PartHtmlError
        else:
            # Look for the table of products.
            products = tree.find(
                'table',
                class_='stickyHeader',
                id='productTable').find('tbody').find_all('tr')

            # Extract the product links for the part numbers from the table.
            product_links = [p.find('td',
                                    class_='digikey-partnumber').a
                             for p in products]

            # Extract all the part numbers from the text portion of the links.
            part_numbers = [l.text for l in product_links]

            # Look for the part number in the list that most closely matches the requested part number.
            match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]

            # Now look for the link that goes with the closest matching part number.
            for l in product_links:
                if l.text == match:
                    # Get the tree for the linked-to page and return that.
                    return get_digikey_part_html_tree(pn,
                                                      url=l['href'],
                                                      descend=descend - 1)

    # If the HTML contains a list of part categories, then give up.
    if tree.find('html', class_='rd-search-parts-page') is not None:
        raise PartHtmlError

    # I don't know what happened here, so give up.
    raise PartHtmlError


def get_mouser_part_html_tree(pn, url=None):
    '''Find the Mouser HTML page for a part number and return the URL and parse tree.'''

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://www.mouser.com/Search/Refine.aspx?Keyword=' + URLL.quote(
            pn,
            safe='')
    elif url[0] == '/':
        url = 'http://www.mouser.com' + url
    elif url.startswith('..'):
        url = 'http://www.mouser.com/Search/' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    url_opener = FakeBrowser()
    html = url_opener.open(url).read()
    tree = BeautifulSoup(html)

    # If the tree contains the tag for a product page, then just return it.
    if tree.find('div', id='product-details') is not None:
        return tree, url

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('table', class_='SearchResultsTable') is not None:
        # Look for the table of products.
        products = tree.find(
            'table',
            class_='SearchResultsTable').find_all(
                'tr',
                class_=('SearchResultsRowOdd', 'SearchResultsRowEven'))

        # Extract the product links for the part numbers from the table.
        product_links = [p.find('div', class_='mfrDiv').a for p in products]

        # Extract all the part numbers from the text portion of the links.
        part_numbers = [l.text for l in product_links]

        # Look for the part number in the list that most closely matches the requested part number.
        match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]

        # Now look for the link that goes with the closest matching part number.
        for l in product_links:
            if l.text == match:
                # Get the tree for the linked-to page and return that.
                return get_mouser_part_html_tree(pn, url=l['href'])

    # I don't know what happened here, so give up.
    raise PartHtmlError


def get_newark_part_html_tree(pn, url=None):
    '''Find the Newark HTML page for a part number and return the URL and parse tree.'''

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://www.newark.com/webapp/wcs/stores/servlet/Search?catalogId=15003&langId=-1&storeId=10194&gs=true&st=' + URLL.quote(
            pn,
            safe='')
    elif url[0] == '/':
        url = 'http://www.newark.com' + url
    elif url.startswith('..'):
        url = 'http://www.newark.com/Search/' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    url_opener = FakeBrowser()
    html = url_opener.open(url).read()
    tree = BeautifulSoup(html)

    # If the tree contains the tag for a product page, then just return it.
    if tree.find('div', class_='productDisplay', id='page') is not None:
        return tree, url

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('table', class_='productLister', id='sProdList') is not None:
        # Look for the table of products.
        products = tree.find('table',
                             class_='productLister',
                             id='sProdList').find_all('tr',
                                                      class_='altRow')

        # Extract the product links for the part numbers from the table.
        product_links = []
        for p in products:
            try:
                product_links.append(
                    p.find('td',
                           class_='mftrPart').find('p',
                                                   class_='wordBreak').a)
            except AttributeError:
                continue

        # Extract all the part numbers from the text portion of the links.
        part_numbers = [l.text for l in product_links]

        # Look for the part number in the list that most closely matches the requested part number.
        match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]

        # Now look for the link that goes with the closest matching part number.
        for l in product_links:
            if l.text == match:
                # Get the tree for the linked-to page and return that.
                return get_newark_part_html_tree(pn, url=l['href'])

    # I don't know what happened here, so give up.
    raise PartHtmlError
