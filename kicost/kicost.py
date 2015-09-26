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

from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import zip
from builtins import range
from builtins import object

import sys
import pprint
import re
import difflib
from bs4 import BeautifulSoup
from random import randint

# ghost library allows scraping pages that have Javascript challenge pages that
# screen-out robots. Digi-Key stopped doing this, so it's not needed at the moment.
# Also requires installation of Qt4.8 (not 5!) and pyside.
#from ghost import Ghost

try:
    from urllib import FancyURLopener, quote as urlquote
except ImportError:
    from urllib.request import FancyURLopener
    from urllib.parse import quote as urlquote

import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range, xl_range_abs

__all__ = ['kicost']  # Only export this routine for use by the outside world.

THIS_MODULE = sys.modules[__name__
                          ]  # Reference to this module for making named calls.

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
        print(msg)


def kicost(in_file, out_filename, debug_level=None):
    '''Take a schematic input file and create an output file with a cost spreadsheet in xlsx format.'''

    global dbg_level
    dbg_level = debug_level

    # Get groups of identical parts.
    parts = get_part_groups(in_file)

    # Get the distributor product page for each part and parse it into a tree.
    debug_print(1, 'Get parsed product page for each component group...')
    for part in parts:
        part.html_trees, part.urls = get_part_html_trees(
            list(distributors.keys()), part)

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
                    print('{} = '.format(f), end=' ')
                    try:
                        pprint.pprint(part.__dict__[f])
                    except KeyError:
                        pass
            print()


def get_part_groups(in_file):
    '''Get groups of identical parts from an XML file and return them as a dictionary.'''

    LIB_DELIMITER = ':'  # Delimiter between library and component name.

    # Read-in the schematic XML file to get a tree and get its root.
    debug_print(1, 'Get schematic XML...')
    root = BeautifulSoup(in_file, 'lxml')

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
            pass  # No fields found for this part.

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
        components[c['ref']] = fields

    # First, get groups of identical components but ignore any manufacturer's
    # part numbers that may be assigned. Just collect those in a list for each group.
    debug_print(1, 'Get groups of identical components...')
    component_groups = {}
    for c in components:

        # Take the field keys and values of each part and create a hash.
        # Use the hash as the key to a dictionary that stores lists of
        # part references that have identical field values.
        # Don't use the manufacturer's part number when calculating the hash!
        fields = components[c]
        hash_fields = {k: fields[k] for k in fields if k != 'manf#'}
        h = hash(tuple(sorted(hash_fields.items())))

        # Now add the hashed component to the group with the matching hash
        # or create a new group if the hash hasn't been seen before.
        try:
            # Add next ref for identical part to the list.
            # No need to add field values since they are the same as the 
            # starting ref field values.
            component_groups[h].refs.append(c)
            # Also add any manufacturer's part number to the group's list.
            try:
                component_groups[h].manf_nums.add(components[c]['manf#'])
            except KeyError:
                # This happens when the part has no manf. part number.
                pass
        except KeyError:
            # This happens if it is the first part in a group, so the group
            # doesn't exist yet.

            class IdenticalComponents(object):
                pass  # Just need a temporary class here.

            component_groups[h] = IdenticalComponents()  # Add empty structure.
            component_groups[h].fields = components[c]  # Store field values.
            component_groups[h].refs = [c]  # Init list of refs with first ref.
            # Now add the manf. part num for this part to the group list,
            # or create an empty list if the part doesn't have a number.
            try:
                component_groups[h].manf_nums = set([components[c]['manf#']])
            except KeyError:
                component_groups[h].manf_nums = set()

    # Some groups of parts may have more than one manufacturer's part number.
    # If so, then partition the group into smaller groups, each having parts
    # with the same manf. part number.
    new_component_groups = {}  # Copy component_groups into this.
    for g in component_groups:
        if len(component_groups[g].manf_nums) > 1:
            # Found a group with two or more manf. part numbers,
            # so partition the group into smaller groups whose members
            # all have the same manf. part number.
            for c in component_groups[g].refs:
                # Calculate a hash of each component's field values like before,
                # only now include the manufacturer's part number.
                h = hash(tuple(sorted(components[c].items())))
                try:
                    # Add next ref for identical part to the list.
                    # No need to add field values since they are the same as the 
                    # starting ref field values.
                    new_component_groups[h].refs.append(c)
                except KeyError:
                    # This happens if it is the first part in a group, so the group
                    # doesn't exist yet. We have to make it.

                    class IdenticalComponents(object):
                        pass  # Just need a temporary class here.

                    new_component_groups[h] = IdenticalComponents(
                    )  # Add empty structure.
                    new_component_groups[h].fields = components[
                        c
                    ]  # Store field values.
                    new_component_groups[h].refs = [
                        c
                    ]  # Init list of refs with first ref.

        elif len(component_groups[g].manf_nums) == 1:
            # This group has a single manf. part number, so there's no need to partition it.
            # Just assign the manf. part number to all the parts.
            new_component_groups[g] = component_groups[g]  # Copy the group.
            new_component_groups[g].fields['manf#'] = component_groups[g].manf_nums.pop(
            )

        else:
            # This group has no manf. part number at all, so leave it blank
            # for all the parts.
            new_component_groups[g] = component_groups[g]  # Copy the group.

    # Now return a list of the groups without their hash keys.
    return list(new_component_groups.values())


def create_spreadsheet(parts, spreadsheet_filename):
    '''Create a spreadsheet using the info for the parts (including their HTML trees).'''

    DEFAULT_BUILD_QTY = 100  # Default value for number of boards to build.
    WORKSHEET_NAME = 'KiCost'  # Default name for part-pricing worksheet.

    # Create spreadsheet file.
    with xlsxwriter.Workbook(spreadsheet_filename) as workbook:

        # Create the various format styles used by various spreadsheet items.
        wrk_formats = {
            'global': workbook.add_format({
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#303030'
            }),
            'digikey': workbook.add_format({
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#CC0000'  # Digi-Key red.
            }),
            'mouser': workbook.add_format({
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#004A85'  # Mouser blue.
            }),
            'newark': workbook.add_format({
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#A2AE06'  # Newark/E14 olive green.
            }),
            'header': workbook.add_format({
                'font_size': 12,
                'bold': True,
                'align': 'center',
                'valign': 'top',
                'text_wrap': True
            }),
            'board_qty': workbook.add_format(
                {'font_size': 13,
                 'bold': True,
                 'align': 'right'}),
            'total_cost_label': workbook.add_format({
                'font_size': 13,
                'bold': True,
                'align': 'right',
                'valign': 'vcenter'
            }),
            'total_cost_currency': workbook.add_format({
                'font_size': 13,
                'font_color': 'red',
                'bold': True,
                'num_format': '$#,##0.00',
                'valign': 'vcenter',
            }),
            'best_price': workbook.add_format({'bg_color': '#80FF80', }),
            'currency': workbook.add_format({'num_format': '$#,##0.00'}),
            'centered_text': workbook.add_format({'align': 'center'}),
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
        # next_col = the column immediately to the right of the global data.
        # qty_col = the column where the quantity needed of each part is stored.
        next_col, refs_col, qty_col = add_globals_to_worksheet(
            wks, wrk_formats, START_ROW, START_COL, TOTAL_COST_ROW, parts)
        # Create a defined range for the global data.
        workbook.define_name(
            'global_part_data', '={wks_name}!{data_range}'.format(
                wks_name=WORKSHEET_NAME,
                data_range=xl_range_abs(START_ROW, START_COL, LAST_PART_ROW,
                                        next_col - 1)))

        # Create the cell where the quantity of boards to assemble is entered.
        # Place the board qty cells near the right side of the global info.
        wks.write(BOARD_QTY_ROW, next_col - 2, 'Board Qty:',
                  wrk_formats['board_qty'])
        wks.write(BOARD_QTY_ROW, next_col - 1, DEFAULT_BUILD_QTY,
                  wrk_formats['board_qty'])  # Set initial board quantity.
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
        for dist in list(distributors.keys()):
            dist_start_col = next_col
            next_col = add_dist_to_worksheet(wks, wrk_formats, START_ROW,
                                             dist_start_col, TOTAL_COST_ROW,
                                             refs_col, qty_col, dist, parts)
            # Create a defined range for each set of distributor part data.
            workbook.define_name(
                '{}_part_data'.format(dist), '={wks_name}!{data_range}'.format(
                    wks_name=WORKSHEET_NAME,
                    data_range=xl_range_abs(START_ROW, dist_start_col,
                                            LAST_PART_ROW, next_col - 1)))


def collapse_refs(refs):
    '''Collapse list of part references into a sorted, comma-separated list of hyphenated ranges.'''

    def convert_to_ranges(nums):
        '''Collapse a list of numbers into sorted, comma-separated, hyphenated ranges.
           e.g.: 3,4,7,8,9,10,11,13,14 => 3,4,7-11,13,14'''
        nums.sort()  # Sort all the numbers.
        num_ranges = []  # No ranges found yet since we just started.
        range_start = 0  # First possible range is at the start of the list of numbers.
        # Go through the list of numbers looking for 3 or more sequential numbers.
        while range_start < len(nums):
            num_range = nums[range_start
                             ]  # Current range starts off as a single number.
            next_range_start = range_start + 1  # The next possible start of a range.
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

    prefix_nums = {}  # Contains a list of numbers for each distinct prefix.
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
    for prefix in list(prefix_nums.keys()):
        prefix_nums[prefix] = convert_to_ranges(prefix_nums[prefix])

        # Combine the prefixes and number ranges back into part references.
    collapsed_refs = []
    for prefix, nums in list(prefix_nums.items()):
        for num in nums:
            if type(num) == list:
                # Convert a range list into a collapsed part reference:
                # e.g., 'R10-R15' from 'R':[10,15].
                collapsed_refs.append('{0}{1}-{0}{2}'.format(prefix, num[0],
                                                             num[-1]))
            elif type(num) == int:
                # Convert a single number into a simple part reference: e.g., 'R10'.
                collapsed_refs.append('{}{}'.format(prefix, num))
            else:
                raise Exception('Unknown part reference {}{}'.format(prefix,
                                                                     num))

                # Return the collapsed par references.
    return collapsed_refs


def add_globals_to_worksheet(wks, wrk_formats, start_row, start_col,
                             total_cost_row, parts):
    '''Add global part data to the spreadsheet.'''

    # Columns for the various types of global part data.
    columns = {
        'refs': {
            'col': 0,
            'level': 0,  # Outline level (or hierarchy level) for this column.
            'label': 'Refs',
            'width': None,  # Column width (default in this case).
            'comment': 'Schematic identifier for each part.'
        },
        'value': {
            'col': 1,
            'level': 0,
            'label': 'Value',
            'width': None,
            'comment': 'Value of each part.'
        },
        'desc': {
            'col': 2,
            'level': 0,
            'label': 'Desc',
            'width': None,
            'comment': 'Description of each part.'
        },
        'footprint': {
            'col': 3,
            'level': 0,
            'label': 'Footprint',
            'width': None,
            'comment': 'PCB footprint for each part.'
        },
        'manf': {
            'col': 4,
            'level': 0,
            'label': 'Manf',
            'width': None,
            'comment': 'Manufacturer of each part.'
        },
        'manf#': {
            'col': 5,
            'level': 0,
            'label': 'Manf#',
            'width': None,
            'comment': 'Manufacturer number for each part.'
        },
        'qty': {
            'col': 6,
            'level': 0,
            'label': 'Qty',
            'width': None,
            'comment': 'Total number of each part needed to assemble the board.'
        },
        'unit_price': {
            'col': 7,
            'level': 0,
            'label': 'Unit$',
            'width': None,
            'comment':
            'Minimum unit price for each part across all distributors.'
        },
        'ext_price': {
            'col': 8,
            'level': 0,
            'label': 'Ext$',
            'width': 15,  # Displays up to $9,999,999.99 without "###".
            'comment':
            'Minimum extended price for each part across all distributors.'
        },
        # 'short': {
        # 'col': 7,
        # 'level': 0,
        # 'label': 'Short',
        # 'width': None, # Column width (default in this case).
        # 'comment': 'Shortage of each part needed for assembly.'},
    }
    num_cols = len(list(columns.keys()))

    row = start_row  # Start building global section at this row.

    # Add label for global section.
    wks.merge_range(row, start_col, row, start_col + num_cols - 1,
                    "Global Part Info", wrk_formats['global'])
    row += 1  # Go to next row.

    # Add column headers.
    for k in list(columns.keys()):
        col = start_col + columns[k]['col']
        wks.write_string(row, col, columns[k]['label'], wrk_formats['header'])
        wks.write_comment(row, col, columns[k]['comment'])
        wks.set_column(col, col, columns[k]['width'], None,
                       {'level': columns[k]['level']})
    row += 1  # Go to next row.

    num_parts = len(parts)
    PART_INFO_FIRST_ROW = row  # Starting row of part info.
    PART_INFO_LAST_ROW = PART_INFO_FIRST_ROW + num_parts - 1  # Last row of part info.

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

            # Enter spreadsheet formula for getting the minimum unit price from all the distributors.
        dist_unit_prices = []
        for dist in list(distributors.keys()):
            # Get the name of the data range for this distributor.
            dist_part_data_range = '{}_part_data'.format(dist)
            # Get the contents of the unit price cell for this part (row) and distributor (column+offset).
            dist_unit_prices.append(
                'INDIRECT(ADDRESS(ROW(),COLUMN({})+2))'.format(
                    dist_part_data_range))
        # Create the function that finds the minimum of all the distributor unit price cells for this part.
        min_unit_price_func = '=MINA({})'.format(','.join(dist_unit_prices))
        wks.write(row, start_col + columns['unit_price']['col'],
                  min_unit_price_func, wrk_formats['currency'])

        # Enter spreadsheet formula for calculating minimum extended price.
        wks.write_formula(
            row, start_col + columns['ext_price']['col'],
            '=iferror({qty}*{unit_price},"")'.format(
                qty=xl_rowcol_to_cell(row, start_col + columns['qty']['col']),
                unit_price=xl_rowcol_to_cell(row, start_col +
                                             columns['unit_price']['col'])),
            wrk_formats['currency'])

        # Enter part shortage quantity.
        try:
            wks.write(row, start_col + columns['short']['col'],
                      0)  # slack quantity. (Not handled, yet.)
        except KeyError:
            pass

        row += 1  # Go to next row.

    # Sum the extended prices for all the parts to get the total minimum cost.
    total_cost_col = start_col + columns['ext_price']['col']
    wks.write(total_cost_row, total_cost_col, '=sum({sum_range})'.format(
        sum_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                           PART_INFO_LAST_ROW, total_cost_col)),
              wrk_formats['total_cost_currency'])

    # Return column following the globals so we know where to start next set of cells.
    # Also return the columns where the references and quantity needed of each part is stored.
    return start_col + num_cols, start_col + columns['refs']['col'], start_col + columns['qty']['col']


def add_dist_to_worksheet(wks, wrk_formats, start_row, start_col,
                          total_cost_row, part_ref_col, part_qty_col, dist,
                          parts):
    '''Add distributor-specific part data to the spreadsheet.'''

    # Columns for the various types of distributor-specific part data.
    columns = {
        'avail': {
            'col': 0,
            # column offset within this distributor range of the worksheet.
            'level': 1,  # Outline level (or hierarchy level) for this column.
            'label': 'Avail',  # Column header label.
            'width': None,  # Column width (default in this case).
            'comment': 'Available quantity of each part at the distributor.'
            # Column header tool-tip.
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
    num_cols = len(list(columns.keys()))

    row = start_row  # Start building distributor section at this row.

    # Add label for this distributor.
    wks.merge_range(row, start_col, row, start_col + num_cols - 1,
                    distributors[dist]['label'], wrk_formats[dist])
    row += 1  # Go to next row.

    # Add column headers, comments, and outline level (for hierarchy).
    for k in list(columns.keys()):
        col = start_col + columns[k]['col']  # Column index for this column.
        wks.write_string(row, col, columns[k]['label'], wrk_formats['header'])
        wks.write_comment(row, col, columns[k]['comment'])
        wks.set_column(col, col, columns[k]['width'], None,
                       {'level': columns[k]['level']})
    row += 1  # Go to next row.

    num_parts = len(parts)

    # Add distributor data for each part.
    PART_INFO_FIRST_ROW = row  # Starting row of part info.
    PART_INFO_LAST_ROW = PART_INFO_FIRST_ROW + num_parts - 1  # Last row of part info.

    # Get function names for getting data from the HTML tree for this distributor.
    get_dist_part_num = getattr(THIS_MODULE, 'get_{}_part_num'.format(dist))
    get_dist_qty_avail = getattr(THIS_MODULE, 'get_{}_qty_avail'.format(dist))
    get_dist_price_tiers = getattr(THIS_MODULE,
                                   'get_{}_price_tiers'.format(dist))

    for part in parts:

        # Get the distributor part number from the HTML tree.
        dist_part_num = get_dist_part_num(part.html_trees[dist])

        # If the part number doesn't exist, the distributor doesn't stock this part
        # so leave this row blank.
        if len(dist_part_num) == 0:
            row += 1  # Skip this row and go to the next.
            continue

        # Enter distributor part number for ordering purposes.
        wks.write(row, start_col + columns['part_num']['col'], dist_part_num,
                  None)

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

        purch_qty_col = start_col + columns['purch']['col']
        unit_price_col = start_col + columns['unit_price']['col']
        ext_price_col = start_col + columns['ext_price']['col']

        # Enter a spreadsheet lookup function that determines the unit price based on the needed quantity
        # or the purchased quantity (if that is non-zero), but only if the part number exists.
        wks.write_formula(
            row, unit_price_col,
            '=iferror(lookup(if({purch_qty}="",{needed_qty},{purch_qty}),{{{qtys}}},{{{prices}}}),"")'.format(
                needed_qty=xl_rowcol_to_cell(row, part_qty_col),
                purch_qty=xl_rowcol_to_cell(row, purch_qty_col),
                qtys=','.join(qtys),
                prices=','.join(prices)), wrk_formats['currency'])
        # Conditionally format the unit price cell that contains the best price.
        wks.conditional_format(row, unit_price_col, row, unit_price_col, {
            'type': 'cell',
            'criteria': '<=',
            'value': xl_rowcol_to_cell(row, 7),
            # This is the global data cell holding the minimum unit price for this part. 
            'format': wrk_formats['best_price']
        })

        # Enter the formula for the extended price = purch qty * unit price.
        wks.write_formula(
            row, ext_price_col,
            '=iferror(if({purch_qty}="",{needed_qty},{purch_qty})*{unit_price},"")'.format(
                needed_qty=xl_rowcol_to_cell(row, part_qty_col),
                purch_qty=xl_rowcol_to_cell(row, purch_qty_col),
                unit_price=xl_rowcol_to_cell(row, unit_price_col)),
            wrk_formats['currency'])
        # Conditionally format the extended price cell that contains the best price.
        wks.conditional_format(row, ext_price_col, row, ext_price_col, {
            'type': 'cell',
            'criteria': '<=',
            'value': xl_rowcol_to_cell(row, 8),
            # This is the global data cell holding the minimum extended price for this part.
            'format': wrk_formats['best_price']
        })

        # Enter a link to the distributor webpage for this part.
        wks.write_url(row, start_col + columns['part_url']['col'],
                      part.urls[dist], wrk_formats['centered_text'],
                      string='Link')

        # Finished processing distributor data for this part.
        row += 1  # Go to next row.

    # Sum the extended prices for all the parts to get the total cost from this distributor.
    total_cost_col = start_col + columns['ext_price']['col']
    wks.write(total_cost_row, total_cost_col, '=sum({sum_range})'.format(
        sum_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                           PART_INFO_LAST_ROW, total_cost_col)),
              wrk_formats['total_cost_currency'])

    # Add list of part numbers and purchase quantities for ordering from this distributor.
    ORDER_START_COL = start_col + 1
    ORDER_FIRST_ROW = PART_INFO_LAST_ROW + 2
    ORDER_LAST_ROW = ORDER_FIRST_ROW + num_parts - 1

    # Each distributor has a different format for entering ordering information,
    # so we account for that here.
    order_col = {}
    order_col_numeric = {}
    order_delimiter = {}
    dist_col = {}
    for position, col_tag in enumerate(distributors[dist]['order_cols']):
        order_col[col_tag] = ORDER_START_COL + position  # Column for this order info.
        order_col_numeric[col_tag] = (col_tag ==
                                      'purch')  # Is this order info numeric?
        order_delimiter[col_tag] = distributors[dist][
            'order_delimiter'
        ]  # Delimiter btwn order columns.
        # For the last column of order info, the delimiter is blanked.
        if position + 1 == len(distributors[dist]['order_cols']):
            order_delimiter[col_tag] = ''
        # If the column tag doesn't exist in the list of distributor columns,
        # then assume its for the part reference column in the global data section
        # of the worksheet.
        try:
            dist_col[col_tag] = start_col + columns[col_tag]['col']
        except KeyError:
            dist_col[col_tag] = part_ref_col

    def enter_order_info(info_col, order_col, numeric=False, delimiter=''):
        ''' This function enters a function into a spreadsheet cell that
            prints the information found in info_col into the order_col column
            of the order.
        '''

        # This very complicated spreadsheet function does the following:
        # 1) Computes the set of row indices in the part data that have
        #    non-empty cells in sel_range1 and sel_range2. (Innermost
        #    nested IF and ROW commands.) sel_range1 and sel_range2 are
        #    the part's catalog number and purchase quantity.
        # 2) Selects the k'th smallest of the row indices where k is the
        #    number of rows between the current part row in the order and the
        #    top row of the order. (SMALL() and ROW() commands.)
        # 3) Gets the cell contents  from the get_range using the k'th 
        #    smallest row index found in step #2. (INDEX() command.)
        # 4) Converts the cell contents to a string if it is numeric.
        #    (num_to_text_func is used.) Otherwise, it's already a string.
        # 5) CONCATENATES the string from step #4 with the delimiter
        #    that goes between fields of an order for a part.
        #    (CONCATENATE() command.)
        # 6) If any error occurs (which usually means the indexed cell
        #    contents were blank), then a blank is printed. Otherwise,
        #    the string from step #5 is printed in this cell.
        order_info_func = '''
            IFERROR(
                CONCATENATE(
                    {num_to_text_func}(
                        INDEX(
                            {get_range},
                            SMALL(
                                IF(
                                    {sel_range2} <> "",
                                    IF(
                                        {sel_range1} <> "",
                                        ROW({sel_range1}) - MIN(ROW({sel_range1})) + 1,
                                        ""
                                    ),
                                    ""
                                ),
                                ROW()-ROW({order_first_row})+1
                            )
                        )
                        {num_to_text_fmt}
                    ),
                    {delimiter}
                ),
                ""
            )
        '''

        # Strip all the whitespace from the function string.
        order_info_func = re.sub('[\s\n]', '', order_info_func)

        # This sets the function and conversion format to use if
        # numeric cell contents have to be converted to a string.
        if numeric:
            num_to_text_func = 'TEXT'
            num_to_text_fmt = ',"##0"'
        else:
            num_to_text_func = ''
            num_to_text_fmt = ''

        # This puts the order column delimiter into a form acceptable in a spreadsheet formula.
        if delimiter != '':
            delimiter = '"{}"'.format(delimiter)

        # These are the columns where the part catalog numbers and purchase quantities can be found.
        purch_qty_col = start_col + columns['purch']['col']
        part_num_col = start_col + columns['part_num']['col']

        # Now write the order_info_func into every row of the order in the given column.
        for r in range(ORDER_FIRST_ROW, ORDER_LAST_ROW + 1):
            wks.write_array_formula(
                xl_range(r, order_col, r, order_col),
                '{{={func}}}'.format(func=order_info_func.format(
                    order_first_row=xl_rowcol_to_cell(ORDER_FIRST_ROW, 0,
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

    # For every column in the order info range, enter the part order information.
    for col_tag in ('purch', 'part_num', 'refs'):
        enter_order_info(dist_col[col_tag], order_col[col_tag],
                         numeric=order_col_numeric[col_tag],
                         delimiter=order_delimiter[col_tag])

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
            except (TypeError, AttributeError, ValueError,
                    IndexError):  # Happens when there's no <td> in table row.
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        return price_tiers  # Return empty price tiers.
    return price_tiers


def get_mouser_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Mouser product page.'''
    price_tiers = {}
    try:
        for tr in html_tree.find('div', class_='PriceBreaks').find_all('tr'):
            try:
                qty = int(re.sub('[^0-9]', '',
                                 tr.find('td',
                                         class_='PriceBreakQuantity').a.text))
                unit_price = tr.find('td', class_='PriceBreakPrice').span.text
                price_tiers[qty] = float(re.sub('[^0-9\.]', '', unit_price))
            except (TypeError, AttributeError, ValueError, IndexError):
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        return price_tiers  # Return empty price tiers.
    return price_tiers


def get_mouser_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Newark product page.'''
    price_tiers = {}
    try:
        qty_strs = []
        for qty in html_tree.find('div',
                                  class_='PriceBreaks').find_all(
                                      'div',
                                      class_='PriceBreakQuantity'):
            qty_strs.append(qty.text)
        price_strs = []
        for price in html_tree.find('div',
                                    class_='PriceBreaks').find_all(
                                        'div',
                                        class_='PriceBreakPrice'):
            price_strs.append(price.text)
        qtys_prices = list(zip(qty_strs, price_strs))
        for qty_str, price_str in qtys_prices:
            try:
                qty = re.search('(\s*)([0-9,]+)', qty_str).group(2)
                qty = int(re.sub('[^0-9]', '', qty))
                price_tiers[qty] = float(re.sub('[^0-9\.]', '', price_str))
            except (TypeError, AttributeError, ValueError, IndexError):
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        print('Mouser: no price tiers found.')
        return price_tiers  # Return empty price tiers.
    return price_tiers


def get_newark_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Newark product page.'''
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
        qtys_prices = list(zip(qty_strs, price_strs))
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
    '''Returns True if this Digi-Key part is reeled or Digi-reeled.'''
    qty_tiers = list(get_digikey_price_tiers(html_tree).keys())
    if len(qty_tiers) > 0 and min(qty_tiers) >= 100:
        return True
    if html_tree.find('table',
                      class_='product-details-reel-pricing') is not None:
        return True
    return False


def get_digikey_part_num(html_tree):
    '''Get the part number from the Digikey product page.'''
    try:
        return re.sub('\n', '', html_tree.find('td',
                                               id='reportpartnumber').text)
    except AttributeError:
        return ''


def get_mouser_part_num(html_tree):
    '''Get the part number from the Mouser product page.'''
    try:
        return re.sub('\n', '', html_tree.find('div',
                                               id='divMouserPartNum').text)
    except AttributeError:
        return ''


def get_newark_part_num(html_tree):
    '''Get the part number from the Newark product page.'''
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
    '''Get the available quantity of the part from the Digikey product page.'''
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
    '''Get the available quantity of the part from the Mouser product page.'''
    try:
        # qty_str = html_tree.find(
        # 'table',
        # id='ctl00_ContentMain_availability_tbl1').find_all('td')[0].text
        qty_str = html_tree.find('div',
                                 id='availability').find(
                                     'div',
                                     class_='av-row').find(
                                         'div',
                                         class_='av-col2').text
    except AttributeError as e:
        print('get_mouser_qty_avail exception {}'.format(e))
        return ''
    try:
        qty_str = re.search('(\s*)([0-9,]*)', qty_str, re.IGNORECASE).group(2)
        return int(re.sub('[^0-9]', '', qty_str))
    except ValueError:
        return 0


def get_newark_qty_avail(html_tree):
    '''Get the available quantity of the part from the Newark product page.'''
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


def get_part_html_trees(distributors, part):
    '''Get the parsed HTML trees and page URL from each distributor website for the given part.'''

    html_trees = {}
    urls = {}
    fields = part.fields

    for dist in distributors:
        debug_print(2, '{} {}'.format(dist, part.refs))

        # Get function name for getting the HTML tree for this part from this distributor.
        get_dist_part_html_tree = getattr(THIS_MODULE,
                                          'get_{}_part_html_tree'.format(dist))
        try:
            # Use the distributor's catalog number (if available) to get the page.
            if dist + '#' in fields:
                html_trees[dist], urls[dist] = get_dist_part_html_tree(
                    fields[dist + '#'])
            # Else, use the manufacturer's catalog number (if available) to get the page.
            elif 'manf#' in fields:
                html_trees[dist], urls[dist] = get_dist_part_html_tree(
                    fields['manf#'])
            # Else, give up.
            else:
                raise PartHtmlError
        except (PartHtmlError, AttributeError):
            # If no HTML page was found, then return a tree for an empty page.
            html_trees[dist] = BeautifulSoup('<html></html>', 'lxml')
            urls[dist] = ''

            # Return the parsed HTML trees and the page URLs from whence they came.
    return html_trees, urls


def get_user_agent():
    # The default user_agent_list comprises chrome, IE, firefox, Mozilla, opera, netscape.
    # for more user agent strings,you can find it in http://www.useragentstring.com/pages/useragentstring.php
    user_agent_list = [
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
        "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24"
    ]
    return user_agent_list[randint(0, len(user_agent_list) - 1)]


class FakeBrowser(FancyURLopener):
    ''' This is a fake browser user-agent string so the distributor websites will talk to us.'''
    version = get_user_agent()
    #version = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.124 Safari/537.36'
    #version = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.99 Safari/537.36'
    #version = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6) Gecko/20070725 Firefox/2.0.0.6'
    #version = 'Lynx/2.8.7rel.2 libwww-FM/2.14 SSL-MM/1.4.1 OpenSSL/1.0.0a'
    #version = 'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:1.8.0.7) Gecko/20110321 MultiZilla/4.33.2.6a SeaMonkey/8.6.55'
    #version = 'Python-urllib/3.1'


class PartHtmlError(Exception):
    '''Exception for failed retrieval of an HTML parse tree for a part.'''
    pass


def get_digikey_part_html_tree(pn, url=None, descend=2):
    '''Find the Digikey HTML page for a part number and return the URL and parse tree.'''

    def merge_price_tiers(main_tree, alt_tree):
        '''Merge the price tiers from the alternate-packaging tree into the main tree.'''
        try:
            insertion_point = main_tree.find('table', id='pricing').find('tr')
            for tr in alt_tree.find('table', id='pricing').find_all('tr'):
                insertion_point.insert_after(tr)
        except AttributeError:
            pass

    def merge_qty_avail(main_tree, alt_tree):
        '''Merge the quantities from the alternate-packaging tree into the main tree.'''
        try:
            main_qty = get_digikey_qty_avail(main_tree)
            alt_qty = get_digikey_qty_avail(alt_tree)
            merged_qty = max(main_qty, alt_qty)
            insertion_point = main_tree.find('td', id='quantityavailable')
            insertion_point.string = 'Digi-Key Stock: {}'.format(merged_qty)
        except AttributeError:
            pass

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://www.digikey.com/scripts/DkSearch/dksus.dll?WT.z_header=search_go&lang=en&keywords=' + urlquote(
            pn,
            safe='')
        #url = 'http://www.digikey.com/product-search/en?KeyWords=' + urlquote(pn,safe='') + '&WT.z_header=search_go'
    elif url[0] == '/':
        url = 'http://www.digikey.com' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    url_opener = FakeBrowser()
    html = url_opener.open(url).read()

    # Use the following code if Javascript challenge pages are used to block scrapers.
    # try:
    # ghst = Ghost()
    # sess = ghst.start(plugins_enabled=False, download_images=False, show_scrollbars=False, javascript_enabled=False)
    # html, resources = sess.open(url)
    # print('type of HTML is {}'.format(type(html.content)))
    # html = html.content
    # except Exception as e:
    # print('Exception reading with Ghost: {}'.format(e))

    tree = BeautifulSoup(html, 'lxml')

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

                # Put the main tree on the list as well and then look through
                # the entire list for one that's non-reeled. Use this as the
                # main page for the part.
                ap_trees_and_urls.append((tree, url))
                if digikey_part_is_reeled(tree):
                    for ap_tree, ap_url in ap_trees_and_urls:
                        if not digikey_part_is_reeled(ap_tree):
                            # Found a non-reeled part, so use it as the main page.
                            tree = ap_tree
                            url = ap_url
                            break  # Done looking.

                # Now go through the other pages, merging their pricing and quantity
                # info into the main page.
                for ap_tree, ap_url in ap_trees_and_urls:
                    if ap_tree is tree:
                        continue  # Skip examining the main tree. It already contains its info.
                    try:
                        # Merge the pricing info from that into the main parse tree to make
                        # a single, unified set of price tiers...
                        merge_price_tiers(tree, ap_tree)
                        # and merge available quantity, using the maximum found.
                        merge_qty_avail(tree, ap_tree)
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
        url = 'http://www.mouser.com/Search/Refine.aspx?Keyword=' + urlquote(
            pn,
            safe='')
    elif url[0] == '/':
        url = 'http://www.mouser.com' + url
    elif url.startswith('..'):
        url = 'http://www.mouser.com/Search/' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    url_opener = FakeBrowser()
    html = url_opener.open(url).read()
    tree = BeautifulSoup(html, 'lxml')

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
        url = 'http://www.newark.com/webapp/wcs/stores/servlet/Search?catalogId=15003&langId=-1&storeId=10194&gs=true&st=' + urlquote(
            pn,
            safe='')
    elif url[0] == '/':
        url = 'http://www.newark.com' + url
    elif url.startswith('..'):
        url = 'http://www.newark.com/Search/' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    url_opener = FakeBrowser()
    html = url_opener.open(url).read()
    tree = BeautifulSoup(html, 'lxml')

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
