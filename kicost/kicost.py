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

# Inserted by Pasteurize tool.
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from builtins import zip
from builtins import range
from builtins import int
from builtins import str
from future import standard_library
standard_library.install_aliases()

import future

import sys
import pprint
import copy
import re # Regular expression parser.
import difflib
import logging
import tqdm
import os
from bs4 import BeautifulSoup # XML file interpreter.
import xlsxwriter # XLSX file interpreter.
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range, xl_range_abs
from yattag import Doc, indent  # For generating HTML page for local parts.
import multiprocessing
from multiprocessing import Pool # For running web scrapes in parallel.
from datetime import datetime

try:
    from urllib.parse import urlsplit, urlunsplit
except ImportError:
    from urlparse import quote as urlsplit, urlunsplit

# Stops UnicodeDecodeError exceptions.
try:
    reload(sys)
    sys.setdefaultencoding('utf8')
except NameError:
    pass  # Happens if reload is attempted in Python 3.

class PartHtmlError(Exception):
    '''Exception for failed retrieval of an HTML parse tree for a part.'''
    pass

# ghost library allows scraping pages that have Javascript challenge pages that
# screen-out robots. Digi-Key stopped doing this, so it's not needed at the moment.
# Also requires installation of Qt4.8 (not 5!) and pyside.
#from ghost import Ghost

__all__ = ['kicost']  # Only export this routine for use by the outside world.

SEPRTR = ':'  # Delimiter between library:component, distributor:field, etc.

logger = logging.getLogger('kicost')
DEBUG_OVERVIEW = logging.DEBUG
DEBUG_DETAILED = logging.DEBUG-1
DEBUG_OBSESSIVE = logging.DEBUG-2

# Import information about various distributors.
from . import distributors as distributor_imports
distributors = distributor_imports.distributors

# Import import functions for various EDA tools.
from . import eda_tools as eda_tools_imports
eda_tools = eda_tools_imports.eda_tools
subpart_qty = eda_tools_imports.subpart_qty
from .eda_tools.eda_tools import SUB_SEPRTR

# Regular expression for detecting part reference ids consisting of a
# prefix of letters followed by a sequence of digits, such as 'LED10'
# or a sequence of digits followed by a subpart number like 'CONN1#3'.
# There can even be an interposer character so 'LED-10' is also OK.
PART_REF_REGEX = re.compile('(?P<prefix>[a-z]+\W?)(?P<num>((?P<ref_num>\d+)({}(?P<subpart_num>\d+))?))'.format(SUB_SEPRTR), re.IGNORECASE)

def kicost(in_file, out_filename, user_fields, ignore_fields, variant, num_processes, 
        eda_tool_name, exclude_dist_list, include_dist_list, scrape_retries):
    '''Take a schematic input file and create an output file with a cost spreadsheet in xlsx format.'''

    # Only keep distributors in the included list and not in the excluded list.
    if not include_dist_list:
        include_dist_list = list(distributors.keys())
    rmv_dist = set(exclude_dist_list)
    rmv_dist |= set(list(distributors.keys())) - set(include_dist_list)
    rmv_dist -= set(['local_template'])  # We need this later for creating non-web distributors.
    for dist in rmv_dist:
        distributors.pop(dist, None)

    # Get groups of identical parts.
    eda_tool_module = getattr(eda_tools_imports, eda_tool_name)
    parts, prj_info = eda_tool_module.get_part_groups(in_file, ignore_fields, variant)

    # Create an HTML page containing all the local part information.
    local_part_html = create_local_part_html(parts)
    
    if logger.isEnabledFor(DEBUG_DETAILED):
        pprint.pprint(distributors)

    # Get the distributor product page for each part and scrape the part data.
    logger.log(DEBUG_OVERVIEW, 'Scrape part data for each component group...')
    global scraping_progress
    scraping_progress = tqdm.tqdm(desc='Progress', total=len(parts), unit='part', miniters=1)
    if num_processes <= 1:
        # Scrape data, one part at a time.
        for i in range(len(parts)):
            args = (i, parts[i], distributors, local_part_html, scrape_retries, logger.getEffectiveLevel())
            id, url, part_num, price_tiers, qty_avail = scrape_part(args)
            parts[id].part_num = part_num
            parts[id].url = url
            parts[id].price_tiers = price_tiers
            parts[id].qty_avail = qty_avail
            scraping_progress.update(1)
    else:
        # Create pool of processes to scrape data for multiple parts simultaneously.
        pool = Pool(num_processes)

        # Package part data for passing to each process.
        args = [(i, parts[i], distributors, local_part_html, scrape_retries, logger.getEffectiveLevel()) for i in range(len(parts))]

        # Create a list to store the output from each process.
        results = list(range(len(args)))
        
        # Define a callback routine for updating the scraping progress bar.
        def update(x):
            scraping_progress.update(1)
            return x

        # Start the web scraping processes, one for each part.
        for i in range(len(args)):
            results[i] = pool.apply_async(scrape_part, [args[i]], callback=update)

        # Wait for all the processes to complete.
        pool.close()
        pool.join()

        # Get the data from each process result structure.
        for result in results:
            id, url, part_num, price_tiers, qty_avail = result.get()
            parts[id].part_num = part_num
            parts[id].url = url
            parts[id].price_tiers = price_tiers
            parts[id].qty_avail = qty_avail

    # Done with the scraping progress bar so delete it or else we get an 
    # error when the program terminates.
    del scraping_progress

    # Create the part pricing spreadsheet.
    create_spreadsheet(parts, prj_info, out_filename, user_fields, variant)

    # Print component groups for debugging purposes.
    if logger.isEnabledFor(DEBUG_DETAILED):
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
                    except TypeError:
                        # Pyton 2.7 pprint has some problem ordering None and strings.
                        print(part.__dict__[f])
                    except KeyError:
                        pass
            print()


def create_local_part_html(parts):
    '''Create HTML page containing info for local (non-webscraped) parts.'''

    global distributors
    
    logger.log(DEBUG_OVERVIEW, 'Create HTML page for parts with custom pricing...')
    
    doc, tag, text = Doc().tagtext()
    with tag('html'):
        with tag('body'):
            for p in parts:
                # Find the manufacturer's part number if it exists.
                pn = p.fields.get('manf#') # Returns None if no manf# field.

                # Find the various distributors for this part by
                # looking for leading fields terminated by SEPRTR.
                for key in p.fields:
                    try:
                        dist = key[:key.index(SEPRTR)]
                    except ValueError:
                        continue

                    # If the distributor is not in the list of web-scrapable distributors,
                    # then it's a local distributor. Copy the local distributor template
                    # and add it to the table of distributors.
                    if dist not in distributors:
                        distributors[dist] = copy.copy(distributors['local_template'])
                        distributors[dist]['label'] = dist  # Set dist name for spreadsheet header.

                # Now look for catalog number, price list and webpage link for this part.
                for dist in distributors:
                    cat_num = p.fields.get(dist+':cat#')
                    pricing = p.fields.get(dist+':pricing')
                    link = p.fields.get(dist+':link')
                    if cat_num is None and pricing is None and link is None:
                        continue

                    def make_random_catalog_number(p):
                        hash_fields = {k: p.fields[k] for k in p.fields}
                        hash_fields['dist'] = dist
                        return '#{0:08X}'.format(abs(hash(tuple(sorted(hash_fields.items())))))

                    cat_num = cat_num or pn or make_random_catalog_number(p)
                    p.fields[dist+':cat#'] = cat_num # Store generated cat#.
                    with tag('div', klass=dist+SEPRTR+cat_num):
                        with tag('div', klass='cat#'):
                            text(cat_num)
                        if pricing is not None:
                            with tag('div', klass='pricing'):
                                text(pricing)
                        if link is not None:
                            url_parts = list(urlsplit(link))
                            if url_parts[0] == '':
                                url_parts[0] = u'http'
                            link = urlunsplit(url_parts)
                            with tag('div', klass='link'):
                                text(link)

    # Remove the local distributor template so it won't be processed later on.
    # It has served its purpose.
    del distributors['local_template']

    html = doc.getvalue()
    if logger.isEnabledFor(DEBUG_OBSESSIVE):
        print(indent(html))
    return html


def create_spreadsheet(parts, prj_info, spreadsheet_filename, user_fields, variant):
    '''Create a spreadsheet using the info for the parts (including their HTML trees).'''

    logger.log(DEBUG_OVERVIEW, 'Create spreadsheet...')

    DEFAULT_BUILD_QTY = 100  # Default value for number of boards to build.
    WORKSHEET_NAME = os.path.splitext(os.path.basename(spreadsheet_filename))[0] # Default name for pricing worksheet.

    if len(variant) > 0:
        # Append an indication of the variant to the worksheet title.
        # Remove any special characters that might be illegal in a 
        # worksheet name since the variant might be a regular expression.
        WORKSHEET_NAME = WORKSHEET_NAME + '.' + re.sub(
                                '[\[\]\\\/\|\?\*\:\(\)]','_',variant)

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
            'header': workbook.add_format({
                'font_size': 12,
                'bold': True,
                'align': 'center',
                'valign': 'top',
                'text_wrap': True
            }),
            'board_qty': workbook.add_format({
                'font_size': 13,
                'bold': True,
                'align': 'right'
            }),
            'total_cost_label': workbook.add_format({
                'font_size': 13,
                'bold': True,
                'align': 'right',
                'valign': 'vcenter'
            }),
            'unit_cost_label': workbook.add_format({
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
                'valign': 'vcenter'
            }),
            'unit_cost_currency': workbook.add_format({
                'font_size': 13,
                'font_color': 'green',
                'bold': True,
                'num_format': '$#,##0.00',
                'valign': 'vcenter'
            }),
            'found_part_pct': workbook.add_format({
                'font_size': 12,
                'bold': True,
                'italic': True,
                'valign': 'vcenter'
            }),
            'proj_info_field': workbook.add_format({
                'font_size': 13,
                'bold': True,
                'align': 'right',
                'valign': 'vcenter'
            }),
            'proj_info': workbook.add_format({
                'font_size': 12,
                'align': 'left',
                'valign': 'vcenter'
            }),
            'best_price': workbook.add_format({'bg_color': '#80FF80', }),
            'not_available': workbook.add_format({'bg_color': '#FF0000', 'font_color':'white'}),
            'order_too_much': workbook.add_format({'bg_color': '#FF0000', 'font_color':'white'}),
            'too_few_available': workbook.add_format({'bg_color': '#FF9900', 'font_color':'black'}),
            'too_few_purchased': workbook.add_format({'bg_color': '#FFFF00'}),
            'not_stocked': workbook.add_format({'font_color': '#909090', 'align': 'right' }),
            'currency': workbook.add_format({'num_format': '$#,##0.00'}),
            'centered_text': workbook.add_format({'align': 'center'}),
        }

        # Add the distinctive header format for each distributor to the dict of formats.
        for d in distributors:
            wrk_formats[d] = workbook.add_format(distributors[d]['wrk_hdr_format'])

        # Create the worksheet that holds the pricing information.
        wks = workbook.add_worksheet(WORKSHEET_NAME)

        # Set the row & column for entering the part information in the sheet.
        START_COL = 0
        BOARD_QTY_ROW = 0
        TOTAL_COST_ROW = BOARD_QTY_ROW + 1
        UNIT_COST_ROW = TOTAL_COST_ROW + 1
        START_ROW = 4
        LABEL_ROW = START_ROW + 1
        COL_HDR_ROW = LABEL_ROW + 1
        FIRST_PART_ROW = COL_HDR_ROW + 1
        LAST_PART_ROW = COL_HDR_ROW + len(parts) - 1

        # Load the global part information (not distributor-specific) into the sheet.
        # next_col = the column immediately to the right of the global data.
        # qty_col = the column where the quantity needed of each part is stored.
        next_col, refs_col, qty_col = add_globals_to_worksheet(
            wks, wrk_formats, START_ROW, START_COL, TOTAL_COST_ROW, parts, user_fields)
        # Create a defined range for the global data.
        workbook.define_name(
            'global_part_data', '={wks_name}!{data_range}'.format(
                wks_name= "'" + WORKSHEET_NAME + "'",
                data_range=xl_range_abs(START_ROW, START_COL, LAST_PART_ROW,
                                        next_col - 1)))

        # Add project information to track the project (in a printed version
        # of the BOM) and the date because of price variations.
        wks.write(BOARD_QTY_ROW, START_COL, 'Proj:', wrk_formats['proj_info_field'])
        wks.write(BOARD_QTY_ROW, START_COL+1, prj_info['title'], wrk_formats['proj_info'])
        wks.write(TOTAL_COST_ROW, START_COL, 'Co.:', wrk_formats['proj_info_field'])
        wks.write(TOTAL_COST_ROW, START_COL+1, prj_info['company'], wrk_formats['proj_info'])
        wks.write(UNIT_COST_ROW, START_COL, 'Date:', wrk_formats['proj_info_field'])
        wks.write(UNIT_COST_ROW, START_COL+1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), wrk_formats['proj_info'])

        # Create the cell where the quantity of boards to assemble is entered.
        # Place the board qty cells near the right side of the global info.
        wks.write(BOARD_QTY_ROW, next_col - 2, 'Board Qty:',
                  wrk_formats['board_qty'])
        wks.write(BOARD_QTY_ROW, next_col - 1, DEFAULT_BUILD_QTY,
                  wrk_formats['board_qty'])  # Set initial board quantity.
        # Define the named cell where the total board quantity can be found.
        workbook.define_name('BoardQty', '={wks_name}!{cell_ref}'.format(
            wks_name="'" + WORKSHEET_NAME + "'",
            cell_ref=xl_rowcol_to_cell(BOARD_QTY_ROW, next_col - 1,
                                       row_abs=True,
                                       col_abs=True)))

        # Create the row to show total cost of board parts for each distributor.
        wks.write(TOTAL_COST_ROW, next_col - 2, 'Total Cost:',
                  wrk_formats['total_cost_label'])

        # Define the named cell where the total cost can be found.
        workbook.define_name('TotalCost', '={wks_name}!{cell_ref}'.format(
            wks_name="'" + WORKSHEET_NAME + "'",
            cell_ref=xl_rowcol_to_cell(TOTAL_COST_ROW, next_col - 1,
                                       row_abs=True,
                                       col_abs=True)))


        # Create the row to show unit cost of board parts.
        wks.write(UNIT_COST_ROW, next_col - 2, 'Unit Cost:',
                  wrk_formats['unit_cost_label'])
        wks.write(UNIT_COST_ROW, next_col - 1, "=TotalCost/BoardQty",
                  wrk_formats['unit_cost_currency'])

        # Freeze view of the global information and the column headers, but
        # allow the distributor-specific part info to scroll.
        wks.freeze_panes(COL_HDR_ROW, next_col)

        # Make a list of alphabetically-ordered distributors with web distributors before locals.
        web_dists = sorted([d for d in distributors if distributors[d]['scrape'] != 'local'])
        local_dists = sorted([d for d in distributors if distributors[d]['scrape'] == 'local'])
        dist_list = web_dists + local_dists

        # Load the part information from each distributor into the sheet.
        for dist in dist_list:
            dist_start_col = next_col
            next_col = add_dist_to_worksheet(wks, wrk_formats, START_ROW,
                                             dist_start_col, UNIT_COST_ROW, TOTAL_COST_ROW,
                                             refs_col, qty_col, dist, parts)
            # Create a defined range for each set of distributor part data.
            workbook.define_name(
                '{}_part_data'.format(dist), '={wks_name}!{data_range}'.format(
                    wks_name="'" + WORKSHEET_NAME + "'",
                    data_range=xl_range_abs(START_ROW, dist_start_col,
                                            LAST_PART_ROW, next_col - 1)))


def collapse_refs(refs):
    '''Collapse list of part references into a sorted, comma-separated list of hyphenated ranges.'''

    def convert_to_ranges(nums):
        # Collapse a list of numbers into sorted, comma-separated, hyphenated ranges.
        # e.g.: 3,4,7,8,9,10,11,13,14 => 3,4,7-11,13,14

        def get_refnum(refnum):
            return int(re.match('\d+', refnum).group(0))

        def to_int(n):
            try:
                return int(n)
            except ValueError:
                return n

        nums.sort(key=get_refnum)  # Sort all the numbers.
        nums = [to_int(n) for n in nums]  # Convert strings to ints if possible.
        num_ranges = []  # No ranges found yet since we just started.
        range_start = 0  # First possible range is at the start of the list of numbers.

        # Go through the list of numbers looking for 3 or more sequential numbers.
        while range_start < len(nums):
            num_range = nums[range_start]  # Current range starts off as a single number.
            next_range_start = range_start + 1  # The next possible start of a range.
            # Part references with subparts are never included in ref ranges.
            if not isinstance(num_range, int):
                num_ranges.append(num_range)
                range_start = next_range_start
                continue
            # Look for sequences of three or more sequential numbers.
            for range_end in range(range_start + 2, len(nums)):
                if not isinstance(nums[range_end], int):
                    break  # Ref with subpart, so can't be in a ref range.
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

    prefix_nums = {}  # Contains a list of numbers for each distinct prefix.
    for ref in refs:
        # Partition each part reference into its beginning part prefix and ending number.
        match = re.search(PART_REF_REGEX, ref)
        prefix = match.group('prefix')
        num = match.group('num')

        # Append the number to the list of numbers for this prefix, or create a list
        # with a single number if this is the first time a particular prefix was encountered.
        prefix_nums.setdefault(prefix, []).append(num)

    # Convert the list of numbers for each ref prefix into ranges.
    for prefix in list(prefix_nums.keys()):
        prefix_nums[prefix] = convert_to_ranges(prefix_nums[prefix])

    # Combine the prefixes and number ranges back into part references.
    collapsed_refs = []
    for prefix, nums in list(prefix_nums.items()):
        for num in nums:
            if isinstance(num, list):
                # Convert a range list into a collapsed part reference:
                # e.g., 'R10-R15' from 'R':[10,15].
                collapsed_refs.append('{0}{1}-{0}{2}'.format(prefix, num[0], num[-1]))
            else:
                # Convert a single number into a simple part reference: e.g., 'R10'.
                collapsed_refs.append('{}{}'.format(prefix, num))

    # Return the collapsed par references.
    return collapsed_refs


def add_globals_to_worksheet(wks, wrk_formats, start_row, start_col,
                             total_cost_row, parts, user_fields):
    '''Add global part data to the spreadsheet.'''

    # Columns for the various types of global part data.
    columns = {
        'refs': {
            'col': 0,
            'level': 0,  # Outline level (or hierarchy level) for this column.
            'label': 'Refs',
            'width': None,  # Column width (default in this case).
            'comment': 'Schematic identifier for each part.',
            'static': False,
        },
        'value': {
            'col': 1,
            'level': 0,
            'label': 'Value',
            'width': None,
            'comment': 'Value of each part.',
            'static': True,
        },
        'desc': {
            'col': 2,
            'level': 0,
            'label': 'Desc',
            'width': None,
            'comment': 'Description of each part.',
            'static': True,
        },
        'footprint': {
            'col': 3,
            'level': 0,
            'label': 'Footprint',
            'width': None,
            'comment': 'PCB footprint for each part.',
            'static': True,
        },
        'manf': {
            'col': 4,
            'level': 0,
            'label': 'Manf',
            'width': None,
            'comment': 'Manufacturer of each part.',
            'static': True,
        },
        'manf#': {
            'col': 5,
            'level': 0,
            'label': 'Manf#',
            'width': None,
            'comment': 'Manufacturer number for each part.',
            'static': True,
        },
        'qty': {
            'col': 6,
            'level': 0,
            'label': 'Qty',
            'width': None,
            'comment': '''Total number of each part needed to assemble the board.
Red -> No parts available.
Orange -> Parts available, but not enough.
Yellow -> Enough parts available, but haven't purchased enough.''',
            'static': False,
        },
        'unit_price': {
            'col': 7,
            'level': 0,
            'label': 'Unit$',
            'width': None,
            'comment': 'Minimum unit price for each part across all distributors.',
            'static': False,
        },
        'ext_price': {
            'col': 8,
            'level': 0,
            'label': 'Ext$',
            'width': 15,  # Displays up to $9,999,999.99 without "###".
            'comment': 'Minimum extended price for each part across all distributors.',
            'static': False,
        },
    }

    # Enter user-defined fields into the global part data columns structure.
    for user_field in list(reversed(user_fields)):
        # Skip the user field if it's already in the list of data columns.
        col_ids = list(columns.keys())
        user_field_id = user_field.lower()
        if user_field_id not in col_ids:
            # Put user fields immediately to right of the 'desc' column. 
            desc_col = columns['desc']['col']
            # Push all existing fields to right of 'desc' over by one column.
            for id in col_ids:
                if columns[id]['col'] > desc_col:
                    columns[id]['col'] += 1
            # Insert user field in the vacated space.
            columns[user_field_id] = {
                'col': columns['desc']['col']+1,
                'level': 0,
                'label': user_field,
                'width': None,
                'comment': 'User-defined field.',
                'static': True,
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

    # Add data for each part to the spreadsheet.
    # First, collapse the part references: e.g. J1, J2, J3 => J1-J3.
    for part in parts:
        part.collapsed_refs = ','.join(collapse_refs(part.refs))

    # Then, order the part references with priority ref prefix, ref num, and subpart num.
    def get_ref_key(part):
        match = re.match(PART_REF_REGEX, part.collapsed_refs)
        return [match.group('prefix'), match.group('ref_num'), match.group('subpart_num')]
    parts.sort(key=get_ref_key)

    # Add the global part data to the spreadsheet.
    for part in parts:

        # Enter part references.
        wks.write_string(row, start_col + columns['refs']['col'], part.collapsed_refs)

        # Enter more static data for the part.
        for field in list(columns.keys()):
            if columns[field]['static'] is False:
                continue
            try:
                # Fields found in the XML are lower-cased, so do the same for the column key.
                field_name = field.lower().strip()
                wks.write_string(row, start_col + columns[field]['col'],
                                 part.fields[field_name])
            except KeyError:
                pass

        # Enter total part quantity needed.
        try:
            part_qty = subpart_qty(part);
            wks.write(row, start_col + columns['qty']['col'],
                       part_qty.format('BoardQty') )
            #          '=BoardQty*{}'.format(len(part.refs)))
        except KeyError:
            pass

        # Gather the cell references for calculating minimum unit price and part availability.
        dist_unit_prices = []
        dist_qty_avail = []
        dist_qty_purchased = []
        for dist in list(distributors.keys()):

            # Get the name of the data range for this distributor.
            dist_data_rng = '{}_part_data'.format(dist)

            # Get the contents of the unit price cell for this part (row) and distributor (column+offset).
            dist_unit_prices.append(
                'INDIRECT(ADDRESS(ROW(),COLUMN({})+2))'.format(dist_data_rng))

            # Get the contents of the quantity purchased cell for this part and distributor
            # unless the unit price is not a number in which case return 0.
            dist_qty_purchased.append(
                'IF(ISNUMBER(INDIRECT(ADDRESS(ROW(),COLUMN({0})+2))),INDIRECT(ADDRESS(ROW(),COLUMN({0})+1)),0)'.format(dist_data_rng))

            # Get the contents of the quantity available cell of this part from this distributor.
            dist_qty_avail.append(
                'INDIRECT(ADDRESS(ROW(),COLUMN({})+0))'.format(dist_data_rng))

        # Enter the spreadsheet formula to find this part's minimum unit price across all distributors.
        wks.write_formula(
            row, start_col + columns['unit_price']['col'],
            '=MINA({})'.format(','.join(dist_unit_prices)),
            wrk_formats['currency']
        )

        # Enter the spreadsheet formula for calculating the minimum extended price.
        wks.write_formula(
            row, start_col + columns['ext_price']['col'],
            '=iferror({qty}*{unit_price},"")'.format(
                qty        = xl_rowcol_to_cell(row, start_col + columns['qty']['col']),
                unit_price = xl_rowcol_to_cell(row, start_col + columns['unit_price']['col'])
            ),
            wrk_formats['currency']
        )

        # If part is unavailable from all distributors, color quantity cell red.
        wks.conditional_format(
            row, start_col + columns['qty']['col'],
            row, start_col + columns['qty']['col'],
            {
                'type': 'formula',
                'criteria': '=IF(SUM({})=0,1,0)'.format(','.join(dist_qty_avail)),
                'format': wrk_formats['not_available']
            }
        )

        # If total available part quantity is less than needed quantity, color cell orange. 
        wks.conditional_format(
            row, start_col + columns['qty']['col'],
            row, start_col + columns['qty']['col'],
            {
                'type': 'cell',
                'criteria': '>',
                'value': '=SUM({})'.format(','.join(dist_qty_avail)),
                'format': wrk_formats['too_few_available']
            }
        )

        # If total purchased part quantity is less than needed quantity, color cell yellow. 
        wks.conditional_format(
            row, start_col + columns['qty']['col'],
            row, start_col + columns['qty']['col'],
            {
                'type': 'cell',
                'criteria': '>',
                'value': '=SUM({})'.format(','.join(dist_qty_purchased)),
                'format': wrk_formats['too_few_purchased'],
            }
        )

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
                          unit_cost_row, total_cost_row, part_ref_col, part_qty_col,
                          dist, parts):
    '''Add distributor-specific part data to the spreadsheet.'''

    # Columns for the various types of distributor-specific part data.
    columns = {
        'avail': {
            'col': 0,
            # column offset within this distributor range of the worksheet.
            'level': 1,  # Outline level (or hierarchy level) for this column.
            'label': 'Avail',  # Column header label.
            'width': None,  # Column width (default in this case).
            'comment': '''Available quantity of each part at the distributor.
Red -> No quantity available.
Orange -> Too little quantity available.'''
        },
        'purch': {
            'col': 1,
            'level': 2,
            'label': 'Purch',
            'width': None,
            'comment': 'Purchase quantity of each part from this distributor.\nRed -> Purchasing more than the available quantity.'
        },
        'unit_price': {
            'col': 2,
            'level': 2,
            'label': 'Unit$',
            'width': None,
            'comment': 'Unit price of each part from this distributor.\nGreen -> lowest price.'
        },
        'ext_price': {
            'col': 3,
            'level': 0,
            'label': 'Ext$',
            'width': 15,  # Displays up to $9,999,999.99 without "###".
            'comment':
            '(Unit Price) x (Purchase Qty) of each part from this distributor.\nRed -> Next price break is cheaper.\nGreen -> Cheapest supplier.'
        },
        'part_num': {
            'col': 4,
            'level': 2,
            'label': 'Cat#',
            'width': 15,
            'comment': 'Distributor-assigned catalog number for each part and link to its web page (ctrl-click).'
        },
    }
    num_cols = len(list(columns.keys()))

    row = start_row  # Start building distributor section at this row.

    # Add label for this distributor.
    wks.merge_range(row, start_col, row, start_col + num_cols - 1,
            distributors[dist]['label'].title(), wrk_formats[dist])
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

    for part in parts:

        # Get the distributor part number.
        dist_part_num = part.part_num[dist]

        # Extract price tiers from distributor HTML page tree.
        price_tiers = part.price_tiers[dist]

        # If the part number doesn't exist, just leave this row blank.
        if len(dist_part_num) == 0:
            row += 1  # Skip this row and go to the next.
            continue

        # if len(dist_part_num) == 0 or part.qty_avail[dist] is None or len(list(price_tiers.keys())) == 0:
            # row += 1  # Skip this row and go to the next.
            # continue

        # Enter distributor part number for ordering purposes.
        if dist_part_num:
            wks.write(row, start_col + columns['part_num']['col'], dist_part_num, None)
        else:
            dist_part_num = 'Link' # To use as text for the link.

        # Enter a link to the distributor webpage for this part, even if there
        # is no valid quantity or pricing for the part (see next conditional).
        # Having the link present will help debug if the extraction of the
        # quantity or pricing information was done correctly.
        if part.url[dist]:
            wks.write_url(row, start_col + columns['part_num']['col'],
                part.url[dist],
                string=dist_part_num)

        # Enter quantity of part available at this distributor unless it is None
        # which means the part is not stocked.
        if part.qty_avail[dist]:
            wks.write(row, start_col + columns['avail']['col'],
                  part.qty_avail[dist], None)
        else:
            wks.write(row, start_col + columns['avail']['col'],
                'NonStk', wrk_formats['not_stocked'])
            wks.write_comment(row, start_col + columns['avail']['col'], 
                'This part is listed but is not normally stocked.')

        # Purchase quantity always starts as blank because nothing has been purchased yet.
        wks.write(row, start_col + columns['purch']['col'], '', None)

        # Add pricing information if it exists.
        if len(list(price_tiers)) > 0:
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

            avail_qty_col = start_col + columns['avail']['col']
            purch_qty_col = start_col + columns['purch']['col']
            unit_price_col = start_col + columns['unit_price']['col']
            ext_price_col = start_col + columns['ext_price']['col']

            # Enter a spreadsheet lookup function that determines the unit price based on the needed quantity
            # or the purchased quantity (if that is non-zero).
            wks.write_formula(
                row, unit_price_col,
                '=iferror(lookup(if({purch_qty}="",{needed_qty},{purch_qty}),{{{qtys}}},{{{prices}}}),"")'.format(
                    needed_qty=xl_rowcol_to_cell(row, part_qty_col),
                    purch_qty=xl_rowcol_to_cell(row, purch_qty_col),
                    qtys=','.join([str(q) for q in qtys]),
                    prices=','.join([str(price_tiers[q]) for q in qtys])),
                    wrk_formats['currency'])

            # Add a comment to the cell showing the qty/price breaks.
            price_break_info = 'Qty/Price Breaks:\n  Qty  -  Unit$  -  Ext$\n================'
            for q in qtys[1:]:  # Skip the first qty which is always 0.
                price_break_info += '\n{:>6d} {:>7s} {:>10s}'.format(
                    q,
                    '${:.2f}'.format(price_tiers[q]),
                    '${:.2f}'.format(price_tiers[q] * q))
            wks.write_comment(row, unit_price_col, price_break_info)

            # Conditional format to show no quantity is available.
            wks.conditional_format(
                row, start_col + columns['avail']['col'], 
                row, start_col + columns['avail']['col'],
                {
                    'type': 'cell',
                    'criteria': '==',
                    'value': 0,
                    'format': wrk_formats['not_available']
                }
            )

            # Conditional format to show the avaliable quantity is less than required.
            wks.conditional_format(
                row, start_col + columns['avail']['col'], 
                row, start_col + columns['avail']['col'],
                {
                    'type': 'cell',
                    'criteria': '<',
                    'value': xl_rowcol_to_cell(row, part_qty_col),
                    'format': wrk_formats['too_few_available']
                }
            )

            # Conditional format to show the purchase quantity is more than what is available.
            wks.conditional_format(
                row, start_col + columns['purch']['col'], 
                row, start_col + columns['purch']['col'],
                {
                    'type': 'cell',
                    'criteria': '>',
                    'value': xl_rowcol_to_cell(row, avail_qty_col),
                    'format': wrk_formats['order_too_much']
                }
            )

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

        # Finished processing distributor data for this part.
        row += 1  # Go to next row.

    # Sum the extended prices for all the parts to get the total cost from this distributor.
    total_cost_col = start_col + columns['ext_price']['col']
    wks.write(total_cost_row, total_cost_col, '=sum({sum_range})'.format(
        sum_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                           PART_INFO_LAST_ROW, total_cost_col)),
              wrk_formats['total_cost_currency'])

    # Show how many parts were found at this distributor.
    wks.write(unit_cost_row, total_cost_col,
        '=(ROWS({count_range})-COUNTBLANK({count_range}))&" of "&ROWS({count_range})&" parts found"'.format(
        count_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                           PART_INFO_LAST_ROW, total_cost_col)),
              wrk_formats['found_part_pct'])
    wks.write_comment(unit_cost_row, total_cost_col, 'Number of parts found at this distributor.')

    # Add list of part numbers and purchase quantities for ordering from this distributor.
    ORDER_START_COL = start_col + 1
    ORDER_FIRST_ROW = PART_INFO_LAST_ROW + 3
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
        # This function enters a function into a spreadsheet cell that
        # prints the information found in info_col into the order_col column
        # of the order.

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

    # Write the header and how many parts are being purchased.
    purch_qty_col = start_col + columns['purch']['col']
    ORDER_HEADER =  PART_INFO_LAST_ROW + 2
    wks.write_formula(
        ORDER_HEADER, purch_qty_col,
        '=IFERROR(IF(OR({count_range}),COUNTIF({count_range},">0")&" of "&ROWS({count_range})&" parts purchased",""),"")'.format(
            count_range=xl_range(PART_INFO_FIRST_ROW, purch_qty_col,
                                 PART_INFO_LAST_ROW, purch_qty_col)
        ),
        wrk_formats['found_part_pct']
    )
    wks.write_comment(ORDER_HEADER, purch_qty_col,
        'Copy the information below to the BOM import page of the distributor web site.')

    # For every column in the order info range, enter the part order information.
    for col_tag in ('purch', 'part_num', 'refs'):
        enter_order_info(dist_col[col_tag], order_col[col_tag],
                         numeric=order_col_numeric[col_tag],
                         delimiter=order_delimiter[col_tag])

    return start_col + num_cols  # Return column following the globals so we know where to start next set of cells.


def get_part_html_tree(part, dist, get_html_tree_func, local_part_html, scrape_retries, logger):
    '''Get the HTML tree for a part from the given distributor website or local HTML.'''

    logger.log(DEBUG_OBSESSIVE, '%s %s', dist, str(part.refs))

    for extra_search_terms in set([part.fields.get('manf', ''), '']):
        try:
            # Search for part information using one of the following:
            #    1) the distributor's catalog number.
            #    2) the manufacturer's part number.
            for key in (dist+'#', dist+SEPRTR+'cat#', 'manf#'):
                if key in part.fields:
                    return get_html_tree_func(dist, part.fields[key], extra_search_terms, local_part_html=local_part_html, scrape_retries=scrape_retries)
            # No distributor or manufacturer number, so give up.
            else:
                logger.warning("No '%s#' or 'manf#' field: cannot lookup part %s at %s", dist, part.refs, dist)
                return BeautifulSoup('<html></html>', 'lxml'), ''
                #raise PartHtmlError
        except PartHtmlError:
            pass
        except AttributeError:
            break
    logger.warning("Part %s not found at %s", part.refs, dist)
    # If no HTML page was found, then return a tree for an empty page.
    return BeautifulSoup('<html></html>', 'lxml'), ''


def scrape_part(args):
    '''Scrape the data for a part from each distributor website or local HTML.'''

    id, part, distributor_dict, local_part_html, scrape_retries, log_level = args # Unpack the arguments.

    if multiprocessing.current_process().name == "MainProcess":
        scrape_logger = logging.getLogger('kicost')
    else:
        scrape_logger = multiprocessing.get_logger()
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        scrape_logger.addHandler(handler)
        scrape_logger.setLevel(log_level)

    # Create dictionaries for the various items of part data from each distributor.
    url = {}
    part_num = {}
    price_tiers = {}
    qty_avail = {}

    # Scrape the part data from each distributor website or the local HTML.
    for d in distributor_dict:
        try:
            dist_module = getattr(distributor_imports, d)
        except AttributeError:
            dist_module = getattr(distributor_imports, distributor_dict[d]['module'])

        # Get the HTML tree for the part.
        html_tree, url[d] = get_part_html_tree(part, d, dist_module.get_part_html_tree, local_part_html, scrape_retries, scrape_logger)

        # Call the functions that extract the data from the HTML tree.
        part_num[d] = dist_module.get_part_num(html_tree)
        qty_avail[d] = dist_module.get_qty_avail(html_tree)
        price_tiers[d] = dist_module.get_price_tiers(html_tree)

    # Return the part data.
    return id, url, part_num, price_tiers, qty_avail
