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
import re
import difflib
import logging
import tqdm
from bs4 import BeautifulSoup
from random import randint
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range, xl_range_abs
from yattag import Doc, indent  # For generating HTML page for local parts.
import multiprocessing
from multiprocessing import Pool # For running web scrapes in parallel.
import http.client # For web scraping exceptions.
try:
    from urllib.parse import urlencode, quote as urlquote, urlsplit, urlunsplit
    import urllib.request
    from urllib.request import urlopen, Request
except ImportError:
    from urlparse import quote as urlquote, urlsplit, urlunsplit
    from urllib import urlencode
    from urllib2 import urlopen, Request

# ghost library allows scraping pages that have Javascript challenge pages that
# screen-out robots. Digi-Key stopped doing this, so it's not needed at the moment.
# Also requires installation of Qt4.8 (not 5!) and pyside.
#from ghost import Ghost

__all__ = ['kicost']  # Only export this routine for use by the outside world.

# Used to get the names of functions in this module so they can be called dynamically.
THIS_MODULE = locals()

SEPRTR = ':'  # Delimiter between library:component, distributor:field, etc.
HTML_RESPONSE_RETRIES = 2 # Num of retries for getting part data web page.

WEB_SCRAPE_EXCEPTIONS = (urllib.request.URLError, http.client.HTTPException)
                          
# Global array of distributor names.
distributors = {
    'newark': {
        'scrape': 'web',
        'function': 'newark',
        'label': 'Newark',
        'order_cols': ['part_num', 'purch', 'refs'],
        'order_delimiter': ','
    },
    'digikey': {
        'scrape': 'web',
        'function': 'digikey',
        'label': 'Digi-Key',
        'order_cols': ['purch', 'part_num', 'refs'],
        'order_delimiter': ','
    },
    'mouser': {
        'scrape': 'web',
        'function': 'mouser',
        'label': 'Mouser',
        'order_cols': ['part_num', 'purch', 'refs'],
        'order_delimiter': ' '
    },
}

local_part_html = ''

logger = logging.getLogger('kicost')

DEBUG_OVERVIEW = logging.DEBUG
DEBUG_DETAILED = logging.DEBUG-1
DEBUG_OBSESSIVE = logging.DEBUG-2


def kicost(in_file, out_filename, user_fields, ignore_fields, variant, num_processes):
    '''Take a schematic input file and create an output file with a cost spreadsheet in xlsx format.'''

    # Get groups of identical parts.
    parts = get_part_groups(in_file, ignore_fields, variant)
    
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
            args = (i, parts[i], distributors, local_part_html, logger.getEffectiveLevel())
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
        args = [(i, parts[i], distributors, local_part_html, logger.getEffectiveLevel()) for i in range(len(parts))]

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
    create_spreadsheet(parts, out_filename, user_fields, variant)

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


# Temporary class for storing part group information.
class IdenticalComponents(object):
    pass


def get_part_groups(in_file, ignore_fields, variant):
    '''Get groups of identical parts from an XML file and return them as a dictionary.'''

    ign_fields = [str(f.lower()) for f in ignore_fields]

    def extract_fields(part, variant):
        '''Extract XML fields from the part in a library or schematic.'''

        fields = {}
        try:
            for f in part.find('fields').find_all('field'):
                # Store the name and value for each kicost-related field.
                # Remove case of field name along with leading/trailing whitespace.
                name = str(f['name'].lower().strip())
                if name in ign_fields:
                    continue  # Ignore fields in the ignore list.
                elif SEPRTR not in name: # No separator, so get global field value.
                    fields[name] = str(f.string)
                else:
                    # Now look for fields that start with 'kicost' and possibly
                    # another dot-separated variant field and store their values.
                    # Anything else is in a non-kicost namespace.
                    key_re = 'kicost(\.{})?:(?P<name>.*)'.format(variant)
                    mtch = re.match(key_re, name, flags=re.IGNORECASE)
                    if mtch:
                        # The field name is anything that came after the leading
                        # 'kicost' and variant field.
                        fld_nm = mtch.group('name')
                        # If the field name isn't for a manufacturer's part
                        # number or a distributors catalog number, then add
                        # it to 'local' if it doesn't start with a distributor
                        # name and colon.
                        if fld_nm not in ('manf#', 'manf') and fld_nm[:-1] not in distributors:
                            if SEPRTR not in fld_nm: # This field has no distributor.
                                fld_nm = 'local:' + fld_nm # Assign it to a local distributor.
                        fields[fld_nm] = str(f.string)

        except AttributeError:
            pass  # No fields found for this part.
        return fields

    # Read-in the schematic XML file to get a tree and get its root.
    logger.log(DEBUG_OVERVIEW, 'Get schematic XML...')
    root = BeautifulSoup(in_file, 'lxml')

    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    logger.log(DEBUG_OVERVIEW, 'Get parts library...')
    libparts = {}
    for p in root.find('libparts').find_all('libpart'):

        # Get the values for the fields in each library part (if any).
        fields = extract_fields(p, variant)

        # Store the field dict under the key made from the
        # concatenation of the library and part names.
        libparts[str(p['lib'] + SEPRTR + p['part'])] = fields

        # Also have to store the fields under any part aliases.
        try:
            for alias in p.find('aliases').find_all('alias'):
                libparts[str(p['lib'] + SEPRTR + alias.string)] = fields
        except AttributeError:
            pass  # No aliases for this part.

    # Find the components used in the schematic and elaborate
    # them with global values from the libraries and local values
    # from the schematic.
    logger.log(DEBUG_OVERVIEW, 'Get components...')
    components = {}
    for c in root.find('components').find_all('comp'):

        # Find the library used for this component.
        libsource = c.find('libsource')

        # Create the key to look up the part in the libparts dict.
        libpart = str(libsource['lib'] + SEPRTR + libsource['part'])

        # Initialize the fields from the global values in the libparts dict entry.
        # (These will get overwritten by any local values down below.)
        fields = libparts[libpart].copy()  # Make a copy! Don't use reference!

        # Store the part key and its value.
        fields['libpart'] = libpart
        fields['value'] = str(c.find('value').string)

        # Get the footprint for the part (if any) from the schematic.
        try:
            fields['footprint'] = str(c.find('footprint').string)
        except AttributeError:
            pass

        # Get the values for any other kicost-related fields in the part
        # (if any) from the schematic. These will override any field values
        # from the part library.
        fields.update(extract_fields(c, variant))

        # Store the fields for the part using the reference identifier as the key.
        components[str(c['ref'])] = fields

    # Now partition the parts into groups of like components.
    # First, get groups of identical components but ignore any manufacturer's
    # part numbers that may be assigned. Just collect those in a list for each group.
    logger.log(DEBUG_OVERVIEW, 'Get groups of identical components...')
    component_groups = {}
    for ref, fields in list(components.items()): # part references and field values.

        # Take the field keys and values of each part and create a hash.
        # Use the hash as the key to a dictionary that stores lists of
        # part references that have identical field values. The important fields
        # are the reference prefix ('R', 'C', etc.), value, and footprint.
        # Don't use the manufacturer's part number when calculating the hash!
        # Also, don't use any fields with SEPRTR in the label because that indicates
        # a field used by a specific tool (including kicost).
        hash_fields = {k: fields[k] for k in fields if k not in ('manf#','manf') and SEPRTR not in k}
        h = hash(tuple(sorted(hash_fields.items())))

        # Now add the hashed component to the group with the matching hash
        # or create a new group if the hash hasn't been seen before.
        try:
            # Add next ref for identical part to the list.
            component_groups[h].refs.append(ref)
            # Also add any manufacturer's part number (or None) to the group's list.
            component_groups[h].manf_nums.add(fields.get('manf#'))
        except KeyError:
            # This happens if it is the first part in a group, so the group
            # doesn't exist yet.
            component_groups[h] = IdenticalComponents()  # Add empty structure.
            component_groups[h].refs = [ref]  # Init list of refs with first ref.
            # Now add the manf. part num (or None) for this part to the group set.
            component_groups[h].manf_nums = set([fields.get('manf#')])

    # Now we have groups of seemingly identical parts. But some of the parts
    # within a group may have different manufacturer's part numbers, and these
    # groups may need to be split into smaller groups of parts all having the
    # same manufacturer's number. Here are the cases that need to be handled:
    #   One manf# number: All parts have the same manf#. Don't split this group.
    #   Two manf# numbers, but one is None: Some of the parts have no manf# but
    #       are otherwise identical to the other parts in the group. Don't split
    #       this group. Instead, propagate the non-None manf# to all the parts.
    #   Two manf#, neither is None: All parts have non-None manf# numbers.
    #       Split the group into two smaller groups of parts all having the same
    #       manf#.
    #   Three or more manf#: Split this group into smaller groups, each one with
    #       parts having the same manf#, even if it's None. It's impossible to
    #       determine which manf# the None parts should be assigned to, so leave
    #       their manf# as None.
    new_component_groups = [] # Copy new component groups into this.
    for g, grp in list(component_groups.items()):
        num_manf_nums = len(grp.manf_nums)
        if num_manf_nums == 1:
            new_component_groups.append(grp)
            continue  # Single manf#. Don't split this group.
        elif num_manf_nums == 2 and None in grp.manf_nums:
            new_component_groups.append(grp)
            continue  # Two manf#, but one of them is None. Don't split this group.
        # Otherwise, split the group into subgroups, each with the same manf#.
        for manf_num in grp.manf_nums:
            sub_group = IdenticalComponents()
            sub_group.manf_nums = [manf_num]
            sub_group.refs = []
            for ref in grp.refs:
                # Use get() which returns None if the component has no manf# field.
                # That will match if the group manf_num is also None.
                if components[ref].get('manf#') == manf_num:
                    sub_group.refs.append(ref)
            new_component_groups.append(sub_group)

    # Now get the values of all fields within the members of a group.
    # These will become the field values for ALL members of that group.
    for grp in new_component_groups:
        grp_fields = {}
        for ref in grp.refs:
            for key, val in list(components[ref].items()):
                if val is None: # Field with no value...
                    continue # so ignore it.
                if grp_fields.get(key): # This field has been seen before.
                    if grp_fields[key] != val: # Flag if new field value not the same as old.
                        raise Exception('field value mismatch: {} {} {}'.format(ref, key, val))
                else: # First time this field has been seen in the group, so store it.
                    grp_fields[key] = val
        grp.fields = grp_fields

    # Now return the list of identical part groups.
    return new_component_groups


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
                    if dist not in distributors:
                        distributors[dist] = {
                            'scrape': 'local',
                            'function': 'local',
                            'label': dist,
                            'order_cols': ['purch', 'part_num', 'refs'],
                            'order_delimiter': ''
                        }
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
    html = doc.getvalue()
    if logger.isEnabledFor(DEBUG_OBSESSIVE):
        print(indent(html))
    return html


def create_spreadsheet(parts, spreadsheet_filename, user_fields, variant):
    '''Create a spreadsheet using the info for the parts (including their HTML trees).'''
    
    logger.log(DEBUG_OVERVIEW, 'Create spreadsheet...')

    DEFAULT_BUILD_QTY = 100  # Default value for number of boards to build.
    WORKSHEET_NAME = 'KiCost'  # Default name for part-pricing worksheet.

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
            'local_lbl': [
                workbook.add_format({
                    'font_size': 14,
                    'font_color': 'black',
                    'bold': True,
                    'align': 'center',
                    'valign': 'vcenter',
                    'bg_color': '#909090'  # Darker grey.
                }),
                workbook.add_format({
                    'font_size': 14,
                    'font_color': 'black',
                    'bold': True,
                    'align': 'center',
                    'valign': 'vcenter',
                    'bg_color': '#c0c0c0'  # Lighter grey.
                }),
            ],
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
                'valign': 'vcenter'}),
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
                'valign': 'vcenter'}),
            'unit_cost_currency': workbook.add_format({
                'font_size': 13,
                'font_color': 'green',
                'bold': True,
                'num_format': '$#,##0.00',
                'valign': 'vcenter'
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

        # Define the named cell where the total cost can be found.
        workbook.define_name('TotalCost', '={wks_name}!{cell_ref}'.format(
            wks_name=WORKSHEET_NAME,
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
        index = 0
        for dist in dist_list:
            dist_start_col = next_col
            next_col = add_dist_to_worksheet(wks, wrk_formats, index, START_ROW,
                                             dist_start_col, TOTAL_COST_ROW,
                                             refs_col, qty_col, dist, parts)
            index = (index+1) % 2
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
            'comment': 'Total number of each part needed to assemble the board.',
            'static': False,
        },
        'unit_price': {
            'col': 7,
            'level': 0,
            'label': 'Unit$',
            'width': None,
            'comment':
            'Minimum unit price for each part across all distributors.',
            'static': False,
        },
        'ext_price': {
            'col': 8,
            'level': 0,
            'label': 'Ext$',
            'width': 15,  # Displays up to $9,999,999.99 without "###".
            'comment':
            'Minimum extended price for each part across all distributors.',
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
                'comment': 'User-defined field',
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

    # Add global data for each part.
    for part in parts:

        # Enter part references.
        wks.write_string(row, start_col + columns['refs']['col'],
                         ','.join(collapse_refs(part.refs)))

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


def add_dist_to_worksheet(wks, wrk_formats, index, start_row, start_col,
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
    try:
        wks.merge_range(row, start_col, row, start_col + num_cols - 1,
                    distributors[dist]['label'].title(), wrk_formats[dist])
    except KeyError:
        wks.merge_range(row, start_col, row, start_col + num_cols - 1,
                    distributors[dist]['label'].title(), wrk_formats['local_lbl'][index])
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

        # Enter a link to the distributor webpage for this part, even if there
        # is no valid quantity or pricing for the part (see next conditional).
        # Having the link present will help debug if the extraction of the
        # quantity or pricing information was done correctly.
        if part.url[dist]:
            wks.write_url(row, start_col + columns['part_url']['col'],
                      part.url[dist], wrk_formats['centered_text'],
                      string='Link')

        # If the part number doesn't exist or the part quantity is None 
        # (not the same as 0), then the distributor doesn't stock this part
        # so leave this row blank.
        # Also leave this row blank if the pricing info doesn't exist so a $0
        # price isn't injected that messes up the search for the best price.
        if len(dist_part_num) == 0 or part.qty_avail[dist] is None or len(list(price_tiers.keys())) == 0:
            row += 1  # Skip this row and go to the next.
            continue

        # Enter distributor part number for ordering purposes.
        wks.write(row, start_col + columns['part_num']['col'], dist_part_num,
                  None)

        # Enter quantity of part available at this distributor.
        wks.write(row, start_col + columns['avail']['col'],
                  part.qty_avail[dist], None)

        # Purchase quantity always starts as blank because nothing has been purchased yet.
        wks.write(row, start_col + columns['purch']['col'], '', None)

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
        # or the purchased quantity (if that is non-zero).
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
        for tr in html_tree.find('table', id='product-dollars').find_all('tr'):
            try:
                td = tr.find_all('td')
                qty = int(re.sub('[^0-9]', '', td[0].text))
                price_tiers[qty] = float(re.sub('[^0-9\.]', '', td[1].text))
            except (TypeError, AttributeError, ValueError,
                    IndexError):  # Happens when there's no <td> in table row.
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        logger.log(DEBUG_OBSESSIVE, 'No Digikey pricing information found!')
        return price_tiers  # Return empty price tiers.
    return price_tiers


def get_mouser_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Mouser product page.'''
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
        logger.log(DEBUG_OBSESSIVE, 'No Mouser pricing information found!')
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
        logger.log(DEBUG_OBSESSIVE, 'No Newark pricing information found!')
        return price_tiers  # Return empty price tiers.
    return price_tiers


def get_local_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the local product page.'''
    price_tiers = {}
    try:
        pricing = html_tree.find('div', class_='pricing').text
        pricing = re.sub('[^0-9.;:]', '', pricing) # Keep only digits, decimals, delimiters.
        for qty_price in pricing.split(';'):
            qty, price = qty_price.split(SEPRTR)
            price_tiers[int(qty)] = float(price)
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        logger.log(DEBUG_OBSESSIVE, 'No local pricing information found!')
        return price_tiers  # Return empty price tiers.
    return price_tiers


def digikey_part_is_reeled(html_tree):
    '''Returns True if this Digi-Key part is reeled or Digi-reeled.'''
    qty_tiers = list(get_digikey_price_tiers(html_tree).keys())
    if len(qty_tiers) > 0 and min(qty_tiers) >= 100:
        return True
    return False


def get_digikey_part_num(html_tree):
    '''Get the part number from the Digikey product page.'''
    try:
        return re.sub('\s', '', html_tree.find('td',
                                               id='reportPartNumber').text)
    except AttributeError:
        logger.log(DEBUG_OBSESSIVE, 'No Digikey part number found!')
        return ''


def get_mouser_part_num(html_tree):
    '''Get the part number from the Mouser product page.'''
    try:
        return re.sub('\n', '', html_tree.find('div',
                                               id='divMouserPartNum').text)
    except AttributeError:
        logger.log(DEBUG_OBSESSIVE, 'No Mouser part number found!')
        return ''


def get_newark_part_num(html_tree):
    '''Get the part number from the Newark product page.'''
    try:
        # Newark catalog number is stored in a description list, so get
        # all the list terms and descriptions, strip all the spaces from those,
        # and pair them up.
        div = html_tree.find('div', class_='productDescription').find('dl')
        dt = [re.sub('\s','',d.text) for d in div.find_all('dt')]
        dd = [re.sub('\s','',d.text) for d in div.find_all('dd')]
        dtdd = {k:v for k,v in zip(dt,dd)}  # Pair terms with descriptions.
        return dtdd['NewarkPartNo.:']
    except KeyError:
        logger.log(DEBUG_OBSESSIVE, 'No Newark catalog number found!')
        return '' # No catalog number found in page.
    except AttributeError:
        logger.log(DEBUG_OBSESSIVE, 'No Newark product description found!')
        return '' # No ProductDescription found in page.


def get_local_part_num(html_tree):
    '''Get the part number from the local product page.'''
    try:
        part_num_str = html_tree.find('div', class_='cat#').text
        return part_num_str
    except AttributeError:
        return ''


def get_digikey_qty_avail(html_tree):
    '''Get the available quantity of the part from the Digikey product page.'''
    try:
        qty_tree = html_tree.find('td', id='quantityAvailable').find('span', id='dkQty')
        qty_str = qty_tree.text
    except AttributeError:
        # No quantity found (not even 0) so this is probably a non-stocked part.
        # Return None so the part won't show in the spreadsheet for this dist.
        return None
    try:
        qty_str = re.search('([0-9,]*)', qty_str, re.IGNORECASE).group(1)
        return int(re.sub('[^0-9]', '', qty_str))
    except (AttributeError, ValueError):
        # Didn't find the usual quantity text field. This might be one of those
        # input fields for requesting a quantity, so get the value from the
        # input field.
        try:
            logger.log(DEBUG_OBSESSIVE, 'No Digikey part quantity found!')
            return int(qty_tree.find('input', type='text').get('value'))
        except (AttributeError, ValueError):
            # Well, there's a quantityAvailable section in the website, but
            # it doesn't contain anything decipherable. Let's just assume it's 0.
            return 0


def get_mouser_qty_avail(html_tree):
    '''Get the available quantity of the part from the Mouser product page.'''
    try:
        qty_str = html_tree.find('div',
                                 id='availability').find(
                                     'div',
                                     class_='av-row').find(
                                         'div',
                                         class_='av-col2').text
    except AttributeError as e:
        # No quantity found (not even 0) so this is probably a non-stocked part.
        # Return None so the part won't show in the spreadsheet for this dist.
        logger.log(DEBUG_OBSESSIVE, 'No Mouser part quantity found!')
        return None
    try:
        qty_str = re.search('(\s*)([0-9,]*)', qty_str, re.IGNORECASE).group(2)
        return int(re.sub('[^0-9]', '', qty_str))
    except ValueError:
        # No quantity found (not even 0) so this is probably a non-stocked part.
        # Return None so the part won't show in the spreadsheet for this dist.
        logger.log(DEBUG_OBSESSIVE, 'No Mouser part quantity found!')
        return None


def get_newark_qty_avail(html_tree):
    '''Get the available quantity of the part from the Newark product page.'''
    try:
        # Note that 'availability' is misspelled in the container class name!
        qty_str = html_tree.find('div',
                                 class_='avalabilityContainer').find(
                                     'span',
                                     class_='availability').text
    except (AttributeError, ValueError):
        # No quantity found (not even 0) so this is probably a non-stocked part.
        # Return None so the part won't show in the spreadsheet for this dist.
        return None
    try:
        qty = re.sub('[^0-9]','',qty_str)  # Strip all non-number chars.
        return int(re.sub('[^0-9]', '', qty_str))  # Return integer for quantity.
    except ValueError:
        # No quantity found (not even 0) so this is probably a non-stocked part.
        # Return None so the part won't show in the spreadsheet for this dist.
        logger.log(DEBUG_OBSESSIVE, 'No Newark part quantity found!')
        return None


def get_local_qty_avail(html_tree):
    '''Get the available quantity of the part from the local product page.'''
    try:
        qty_str = html_tree.find('div', class_='quantity').text
    except (AttributeError, ValueError):
        # Return 0 (not None) so this part will show in the spreadsheet
        # even if there is no quantity found.
        return 0
    try:
        return int(re.sub('[^0-9]', '', qty_str))
    except ValueError:
        # Return 0 (not None) so this part will show in the spreadsheet
        # even if there is no quantity found.
        logger.log(DEBUG_OBSESSIVE, 'No local part quantity found!')
        return 0


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


def FakeBrowser(url):
    req = Request(url)
    req.add_header('Accept-Language', 'en-US')
    req.add_header('User-agent', get_user_agent())
    return req


class PartHtmlError(Exception):
    '''Exception for failed retrieval of an HTML parse tree for a part.'''
    pass


def get_digikey_part_html_tree(dist, pn, extra_search_terms='', url=None, descend=2):
    '''Find the Digikey HTML page for a part number and return the URL and parse tree.'''

    def merge_price_tiers(main_tree, alt_tree):
        '''Merge the price tiers from the alternate-packaging tree into the main tree.'''
        try:
            insertion_point = main_tree.find('table', id='product-dollars').find('tr')
            for tr in alt_tree.find('table', id='product-dollars').find_all('tr'):
                insertion_point.insert_after(tr)
        except AttributeError:
            logger.log(DEBUG_OBSESSIVE, 'Problem merging price tiers for Digikey part {} with alternate packaging!'.format(pn))
            pass

    def merge_qty_avail(main_tree, alt_tree):
        '''Merge the quantities from the alternate-packaging tree into the main tree.'''
        try:
            main_qty = get_digikey_qty_avail(main_tree)
            alt_qty = get_digikey_qty_avail(alt_tree)
            if main_qty is None:
                merged_qty = alt_qty
            elif alt_qty is None:
                merged_qty = main_qty
            else:
                merged_qty = max(main_qty, alt_qty)
            if merged_qty is not None:
                insertion_point = main_tree.find('td', id='quantityAvailable').find('span', id='dkQty')
                insertion_point.string = '{}'.format(merged_qty)
        except AttributeError:
            logger.log(DEBUG_OBSESSIVE, 'Problem merging available quantities for Digikey part {} with alternate packaging!'.format(pn))
            pass

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://www.digikey.com/scripts/DkSearch/dksus.dll?WT.z_header=search_go&lang=en&keywords=' + urlquote(
            pn + ' ' + extra_search_terms,
            safe='')
        #url = 'http://www.digikey.com/product-search/en?KeyWords=' + urlquote(pn,safe='') + '&WT.z_header=search_go'
    elif url[0] == '/':
        url = 'http://www.digikey.com' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    req = FakeBrowser(url)
    for _ in range(HTML_RESPONSE_RETRIES):
        try:
            response = urlopen(req)
            html = response.read()
            break
        except WEB_SCRAPE_EXCEPTIONS:
            logger.log(DEBUG_DETAILED,'Exception while web-scraping {} from {}'.format(pn, dist))
            pass
    else: # Couldn't get a good read from the website.
        raise PartHtmlError

    # Use the following code if Javascript challenge pages are used to block scrapers.
    # try:
    # ghst = Ghost()
    # sess = ghst.start(plugins_enabled=False, download_images=False, show_scrollbars=False, javascript_enabled=False)
    # html, resources = sess.open(url)
    # print('type of HTML is {}'.format(type(html.content)))
    # html = html.content
    # except Exception as e:
    # print('Exception reading with Ghost: {}'.format(e))

    try:
        tree = BeautifulSoup(html, 'lxml')
    except Exception:
        raise PartHtmlError

    # If the tree contains the tag for a product page, then return it.
    if tree.find('div', class_='product-top-section') is not None:

        # Digikey separates cut-tape and reel packaging, so we need to examine more pages
        # to get all the pricing info. But don't descend any further if limit has been reached.
        if descend > 0:
            try:
                # Find all the URLs to alternate-packaging pages for this part.
                ap_urls = [
                    ap.find('li', class_='lnkAltPack').find_all('a')[-1].get('href')
                    for ap in tree.find(
                        'div', class_='bota',
                        id='additionalPackaging').find_all(
                            'ul', class_='more-expander-item')
                ]
                logger.log(DEBUG_OBSESSIVE,'Found {} alternate packagings for {} from {}'.format(len(ap_urls), pn, dist))
                try:
                    ap_trees_and_urls = [get_digikey_part_html_tree(dist, pn, 
                                     extra_search_terms, ap_url, descend=0)
                                     for ap_url in ap_urls]
                except Exception:
                    logger.log(DEBUG_OBSESSIVE,'Failed to find alternate packagings for {} from {}'.format(pn, dist))

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
                        logger.log(DEBUG_OBSESSIVE,'Problem merging price/qty for {} from {}'.format(pn, dist))
                        continue
            except AttributeError:
                logger.log(DEBUG_OBSESSIVE,'Problem parsing URLs from product page for {} from {}'.format(pn, dist))
                pass
        return tree, url  # Return the parse tree and the URL where it came from.

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('table', id='productTable') is not None:
        logger.log(DEBUG_OBSESSIVE,'Found product table for {} from {}'.format(pn, dist))
        if descend <= 0:
            raise PartHtmlError
        else:
            # Look for the table of products.
            products = tree.find(
                'table',
                id='productTable').find('tbody').find_all('tr')

            # Extract the product links for the part numbers from the table.
            # Extract links for both manufacturer and catalog numbers.
            product_links = [p.find('td',
                                    class_='tr-mfgPartNumber').a
                             for p in products]
            product_links.extend([p.find('td',
                                    class_='tr-dkPartNumber').a
                             for p in products])

            # Extract all the part numbers from the text portion of the links.
            part_numbers = [l.text for l in product_links]

            # Look for the part number in the list that most closely matches the requested part number.
            match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]

            # Now look for the link that goes with the closest matching part number.
            for l in product_links:
                if l.text == match:
                    # Get the tree for the linked-to page and return that.
                    logger.log(DEBUG_OBSESSIVE,'Selecting {} from product table for {} from {}'.format(l.text, pn, dist))
                    return get_digikey_part_html_tree(dist, pn, extra_search_terms,
                                                      url=l['href'],
                                                      descend=descend - 1)

    # If the HTML contains a list of part categories, then give up.
    if tree.find('form', id='keywordSearchForm') is not None:
        raise PartHtmlError

    # I don't know what happened here, so give up.
    raise PartHtmlError


def get_mouser_part_html_tree(dist, pn, extra_search_terms='', url=None, descend=2):
    '''Find the Mouser HTML page for a part number and return the URL and parse tree.'''

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://www.mouser.com/Search/Refine.aspx?Keyword=' + urlquote(
            pn + ' ' + extra_search_terms,
            safe='')
    elif url[0] == '/':
        url = 'http://www.mouser.com' + url
    elif url.startswith('..'):
        url = 'http://www.mouser.com/Search/' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    req = FakeBrowser(url)
    req.add_header('Cookie', 'preferences=ps=www2&pl=en-US&pc_www2=USDe')
    for _ in range(HTML_RESPONSE_RETRIES):
        try:
            response = urlopen(req)
            html = response.read()
            break
        except WEB_SCRAPE_EXCEPTIONS:
            logger.log(DEBUG_DETAILED,'Exception while web-scraping {} from {}'.format(pn, dist))
            pass
    else: # Couldn't get a good read from the website.
        raise PartHtmlError

    try:
        tree = BeautifulSoup(html, 'lxml')
    except Exception:
        raise PartHtmlError

    # If the tree contains the tag for a product page, then just return it.
    if tree.find('div', id='product-details') is not None:
        return tree, url

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('table', class_='SearchResultsTable') is not None:
        if descend <= 0:
            raise PartHtmlError
        else:
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
                    return get_mouser_part_html_tree(dist, pn, extra_search_terms,
                                url=l['href'], descend=descend-1)

    # I don't know what happened here, so give up.
    raise PartHtmlError


def get_newark_part_html_tree(dist, pn, extra_search_terms='', url=None, descend=2):
    '''Find the Newark HTML page for a part number and return the URL and parse tree.'''

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://www.newark.com/webapp/wcs/stores/servlet/Search?catalogId=15003&langId=-1&storeId=10194&gs=true&st=' + urlquote(
            pn + ' ' + extra_search_terms,
            safe='')
    elif url[0] == '/':
        url = 'http://www.newark.com' + url
    elif url.startswith('..'):
        url = 'http://www.newark.com/Search/' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    for _ in range(HTML_RESPONSE_RETRIES):
        try:
            req = FakeBrowser(url)
            response = urlopen(req)
            html = response.read()
            break
        except WEB_SCRAPE_EXCEPTIONS:
            logger.log(DEBUG_DETAILED,'Exception while web-scraping {} from {}'.format(pn, dist))
            pass
    else: # Couldn't get a good read from the website.
        raise PartHtmlError

    try:
        tree = BeautifulSoup(html, 'lxml')
    except Exception:
        raise PartHtmlError

    # If the tree contains the tag for a product page, then just return it.
    if tree.find('div', class_='productDisplay', id='page') is not None:
        return tree, url

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('table', class_='productLister', id='sProdList') is not None:
        if descend <= 0:
            raise PartHtmlError
        else:
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
                    return get_newark_part_html_tree(dist, pn, extra_search_terms,
                                url=l['href'], descend=descend-1)

    # I don't know what happened here, so give up.
    raise PartHtmlError


def get_local_part_html_tree(dist, pn, extra_search_terms='', url=None):
    '''Extract the HTML tree from the HTML page for local parts.'''

    # Extract the HTML tree from the local part HTML page.
    html = local_part_html
    try:
        tree = BeautifulSoup(html, 'lxml')
    except Exception:
        raise PartHtmlError

    try:
        # Find the DIV in the tree for the given part and distributor.
        class_ = dist + SEPRTR + pn
        part_tree = tree.find('div', class_=class_)
        url_tree = part_tree.find('div', class_='link')
        try:
            # Return the part data tree and any URL associated with the part.
            return part_tree, url_tree.text.strip()
        except AttributeError:
            # Return part data tree and None if the URL is not found.
            return part_tree, None
    except AttributeError:
        # Return an error if the part_tree is not found.
        raise PartHtmlError


def get_part_html_tree(part, dist, distributor_dict, local_html, logger):
    '''Get the HTML tree for a part from the given distributor website or local HTML.'''

    global local_part_html
    local_part_html = local_html

    logger.log(DEBUG_OBSESSIVE, '%s %s', dist, str(part.refs))
    
    # Get function name for getting the HTML tree for this part from this distributor.
    function = distributor_dict[dist]['function']
    get_dist_part_html_tree = THIS_MODULE['get_{}_part_html_tree'.format(function)]

    try:
        # Search for part information using one of the following:
        #    1) the distributor's catalog number.
        #    2) the manufacturer's part number.
        extra_search_terms = part.fields.get('manf', '')
        for key in (dist+'#', dist+SEPRTR+'cat#', 'manf#'):
            if key in part.fields:
                return get_dist_part_html_tree(dist, part.fields[key], extra_search_terms)
        # No distributor or manufacturer number, so give up.
        else:
            logger.warning("No '%s#' or 'manf#' field: cannot lookup part %s at %s", dist, part.refs, dist)
            return BeautifulSoup('<html></html>', 'lxml'), ''
    except (PartHtmlError, AttributeError):
        logger.warning("Part %s not found at %s", part.refs, dist)
        # If no HTML page was found, then return a tree for an empty page.
        return BeautifulSoup('<html></html>', 'lxml'), ''


def scrape_part(args):
    '''Scrape the data for a part from each distributor website or local HTML.'''

    id, part, distributor_dict, local_html, log_level = args # Unpack the arguments.

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
        # Get the HTML tree for the part.
        html_tree, url[d] = get_part_html_tree(part, d, distributor_dict, local_html, scrape_logger)

        # Get the function names for getting the part data from the HTML tree.
        function = distributor_dict[d]['function']
        get_dist_price_tiers = THIS_MODULE['get_{}_price_tiers'.format(function)]
        get_dist_part_num = THIS_MODULE['get_{}_part_num'.format(function)]
        get_dist_qty_avail = THIS_MODULE['get_{}_qty_avail'.format(function)]

        # Call the functions that extract the data from the HTML tree.
        part_num[d] = get_dist_part_num(html_tree)
        qty_avail[d] = get_dist_qty_avail(html_tree)
        price_tiers[d] = get_dist_price_tiers(html_tree)

    # Return the part data.
    return id, url, part_num, price_tiers, qty_avail
