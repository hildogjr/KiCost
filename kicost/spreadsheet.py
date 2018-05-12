# -*- coding: utf-8 -*- 
# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Júnior
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

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# Python libraries.
import os
from datetime import datetime
import re # Regular expression parser.
import xlsxwriter # XLSX file interpreter.
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range, xl_range_abs
# KiCost libraries.
from . import __version__ # Version control by @xesscorp.
from .globals import SEPRTR
from .globals import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE
from .distributors import distributor_dict # Distributors names and definitions to use in the spreadsheet.
from .eda_tools.eda_tools import partgroup_qty, order_refs, PART_REF_REGEX

__all__ = ['create_spreadsheet']

# Regular expression to the link for one datasheet.
DATASHEET_LINK_REGEX = re.compile('^(http(s)?:\/\/)?(www.)?[0-9a-z\.]+\/[0-9a-z\.\/\%\-\_]+(.pdf)?$', re.IGNORECASE)

# Extra information characteristics of the components gotten in the page that will be displayed as comment in the 'cat#' column.
EXTRA_INFO_DISPLAY = ['value', 'tolerance', 'footprint', 'power', 'current', 'voltage', 'frequency', 'temp_coeff', 'manf', 'size']


def create_spreadsheet(parts, prj_info, spreadsheet_filename, collapse_refs, user_fields, variant):
    '''Create a spreadsheet using the info for the parts (including their HTML trees).'''
    
    logger.log(DEBUG_OVERVIEW, 'Creating the \'{}\' spreadsheet...'.format(
                                    os.path.basename(spreadsheet_filename)) )
    
    MAX_LEN_WORKSHEET_NAME = 31 # Microsoft Excel allows a 31 characters longer
                                # string for the worksheet name, Google
                                #Spreadsheet 100 and LibreOffice Calc have no limit.
    DEFAULT_BUILD_QTY = 100  # Default value for number of boards to build.
    WORKSHEET_NAME = os.path.splitext(os.path.basename(spreadsheet_filename))[0] # Default name for pricing worksheet.
    
    if len(variant) > 0:
        # Append an indication of the variant to the worksheet title.
        # Remove any special characters that might be illegal in a 
        # worksheet name since the variant might be a regular expression.
        # Fix the maximum worksheet name, priorize the variant string cutting
        # the board project.
        variant = re.sub('[\[\]\\\/\|\?\*\:\(\)]','_',
                            variant[:(MAX_LEN_WORKSHEET_NAME)])
        WORKSHEET_NAME += '.'
        WORKSHEET_NAME = WORKSHEET_NAME[:(MAX_LEN_WORKSHEET_NAME-len(variant))]
        WORKSHEET_NAME += variant
    else:
        WORKSHEET_NAME = WORKSHEET_NAME[:MAX_LEN_WORKSHEET_NAME]
    
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
            'part_format': workbook.add_format({
                'valign': 'vcenter'
            }),
            'found_part_pct': workbook.add_format({
                'font_size': 10,
                'bold': True,
                'italic': True,
                'valign': 'vcenter'
            }),
            'best_price': workbook.add_format({'bg_color': '#80FF80', }),
            'not_manf_codes': workbook.add_format({'bg_color': '#AAAAAA'}),
            'not_available': workbook.add_format({'bg_color': '#FF0000', 'font_color':'white'}),
            'order_too_much': workbook.add_format({'bg_color': '#FF0000', 'font_color':'white'}),
            'too_few_available': workbook.add_format({'bg_color': '#FF9900', 'font_color':'black'}),
            'too_few_purchased': workbook.add_format({'bg_color': '#FFFF00'}),
            'not_stocked': workbook.add_format({'font_color': '#909090', 'align': 'right', 'valign': 'vcenter'}),
            'currency': workbook.add_format({'num_format': '$#,##0.00', 'valign': 'vcenter'}),
        }

        # Add the distinctive header format for each distributor to the `dict` of formats.
        for d in distributor_dict:
            wrk_formats[d] = workbook.add_format(distributor_dict[d]['wrk_hdr_format'])

        # Create the worksheet that holds the pricing information.
        wks = workbook.add_worksheet(WORKSHEET_NAME)

        # Set the row & column for entering the part information in the sheet.
        START_COL = 0
        BOARD_QTY_ROW = 0
        UNIT_COST_ROW = BOARD_QTY_ROW + 1
        TOTAL_COST_ROW = BOARD_QTY_ROW + 2
        START_ROW = 1+3*len(prj_info)
        LABEL_ROW = START_ROW + 1
        COL_HDR_ROW = LABEL_ROW + 1
        FIRST_PART_ROW = COL_HDR_ROW + 1
        LAST_PART_ROW = COL_HDR_ROW + len(parts) - 1
        next_row = 0

        # Load the global part information (not distributor-specific) into the sheet.
        # next_col = the column immediately to the right of the global data.
        # qty_col = the column where the quantity needed of each part is stored.
        next_col, refs_col, qty_col = add_globals_to_worksheet(
            wks, wrk_formats, START_ROW, START_COL, TOTAL_COST_ROW,
            parts, user_fields, collapse_refs)
        # Create a defined range for the global data.
        workbook.define_name(
            'global_part_data', '={wks_name}!{data_range}'.format(
                wks_name= "'" + WORKSHEET_NAME + "'",
                data_range=xl_range_abs(START_ROW, START_COL, LAST_PART_ROW,
                                        next_col - 1)))

        for i_prj in range(len(prj_info)):
            # Add project information to track the project (in a printed version
            # of the BOM) and the date because of price variations.
            i_prj_str = (str(i_prj) if len(prj_info)>1 else '')
            wks.write(next_row, START_COL,
                      'Prj{}:'.format(i_prj_str),
                      wrk_formats['proj_info_field'])
            wks.write(next_row, START_COL+1,
                      prj_info[i_prj]['title'], wrk_formats['proj_info'])
            wks.write(next_row+1, START_COL, 'Co.:',
                      wrk_formats['proj_info_field'])
            wks.write(next_row+1, START_COL+1,
                      prj_info[i_prj]['company'], wrk_formats['proj_info'])
            wks.write(next_row+2, START_COL,
                      'Prj date:', wrk_formats['proj_info_field'])
            wks.write(next_row+2, START_COL+1,
                      prj_info[i_prj]['date'], wrk_formats['proj_info'])

            # Create the cell where the quantity of boards to assemble is entered.
            # Place the board qty cells near the right side of the global info.
            wks.write(next_row, next_col - 2, 'Board Qty{}:'.format(i_prj_str),
                      wrk_formats['board_qty'])
            wks.write(next_row, next_col - 1, DEFAULT_BUILD_QTY,
                      wrk_formats['board_qty'])  # Set initial board quantity.
            # Define the named cell where the total board quantity can be found.
            workbook.define_name('BoardQty{}'.format(i_prj_str),
                '={wks_name}!{cell_ref}'.format(
                    wks_name="'" + WORKSHEET_NAME + "'",
                    cell_ref=xl_rowcol_to_cell(next_row, next_col - 1,
                                           row_abs=True,
                                           col_abs=True)))
            
            # Create the cell to show total cost of board parts for each distributor.
            wks.write(next_row + 2, next_col - 2, 'Total Cost{}:'.format(i_prj_str),
                      wrk_formats['total_cost_label'])
            # Define the named cell where the total cost can be found.
            workbook.define_name('TotalCost{}'.format(i_prj_str),
                            '={wks_name}!{cell_ref}'.format(
                                wks_name="'" + WORKSHEET_NAME + "'",
                                cell_ref=xl_rowcol_to_cell(next_row + 2*(1+i_prj),
                                                           next_col - 1,
                                       row_abs=True, col_abs=True)) )

            # Create the cell to show unit cost of (each project) board parts.
            wks.write(next_row+1, next_col - 2, 'Unit Cost{}:'.format(i_prj_str),
                      wrk_formats['unit_cost_label'])
            wks.write(next_row+1, next_col - 1,
                      "=TotalCost{}/BoardQty{}".format(i_prj_str, i_prj_str),
                      wrk_formats['unit_cost_currency'])

            next_row += 3

        # Add general information of the scrap to track price modifications.
        wks.write(next_row, START_COL,
                  '$ date:', wrk_formats['proj_info_field'])
        wks.write(next_row, START_COL+1,
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"), wrk_formats['proj_info'])
        # Add the total cost of all projects together.
        if len(prj_info)>1:
            # Create the row to show total cost of board parts for each distributor.
            wks.write(next_row, next_col - 2, 'Total Prjs Cost:',
                      wrk_formats['total_cost_label'])
            # Define the named cell where the total cost can be found.
            workbook.define_name('TotalCost', '={wks_name}!{cell_ref}'.format(
                            wks_name="'" + WORKSHEET_NAME + "'",
                            cell_ref=xl_rowcol_to_cell(next_row, next_col - 1,
                                       row_abs=True,
                                       col_abs=True)))
        next_row += 1

        # Freeze view of the global information and the column headers, but
        # allow the distributor-specific part info to scroll.
        wks.freeze_panes(COL_HDR_ROW, next_col)

        # Make a list of alphabetically-ordered distributors with web distributors before locals.
        logger.log(DEBUG_OVERVIEW, 'Sorting the distributors...')
        web_dists = sorted([d for d in distributor_dict if distributor_dict[d]['scrape'] != 'local'])
        local_dists = sorted([d for d in distributor_dict if distributor_dict[d]['scrape'] == 'local'])
        dist_list = web_dists + local_dists

        # Load the part information from each distributor into the sheet.
        logger.log(DEBUG_OVERVIEW, 'Writing the distributors parts informations...')
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

        # Add the KiCost package information at the end of the spreadsheet to debug
        # information at the forum and "advertising".
        wks.write(START_ROW+len(parts)+3, START_COL,
            'Distributors scraped by KiCost\N{REGISTERED SIGN} v.' + __version__,
                wrk_formats['proj_info'])


def add_globals_to_worksheet(wks, wrk_formats, start_row, start_col,
                             total_cost_row, parts, user_fields, collapse_refs):
    '''Add global part data to the spreadsheet.'''

    logger.log(DEBUG_OVERVIEW, 'Writing the global parts informations...')

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
            'comment': 'Manufacturer number for each part and link to it\'s datasheet (ctrl-click).',
            'static': True,
        },
        'qty': {
            'col': 6,
            'level': 0,
            'label': 'Qty',
            'width': None,
            'comment': '''Total number of each part needed to assemble the board(s).
Gray -> Not manf# codes.
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

    # Remove not used columns by the field not founded in ALL the parts. This give
    # better visualization on notebooks (small screens) and optimization to print.
    def remove_col_not_exist_parts(code):
        def remove_column(name):
            for h in columns:
                if columns[h]['col']>columns[name]['col']:
                    columns[h]['col'] -= 1
            del columns[name]
        for part in parts:
            try:
                if part.fields[code]:
                    return
            except KeyError:
                pass
        remove_column(code) # All 'manf' are empty.
    remove_col_not_exist_parts('manf')
    remove_col_not_exist_parts('desc')

    # Add quantity columns to deal with different quantities in the BOM files. The
    # original quantity column will be the total of each item. For check the number
    # of BOM files read, see the length of p[?]['manf#_qty'], if it is a `list()`
    # instance, if don't, the length is always `1`.
    num_prj = max([len(part.fields.get('manf#_qty',[])) if isinstance(part.fields.get('manf#_qty',[]),list) else 1 for part in parts])
    if num_prj>1:
        for i_prj in range(num_prj):
            # Add one column to quantify the quantity for each project.
            name = 'qty_prj{}'.format(i_prj)
            col = columns['qty']['col']
            columns[name] = columns['qty'].copy()
            columns[name]['col'] = col
            columns[name]['label'] = 'Qty.Prj{}'.format(i_prj)
            columns[name]['comment'] = 'Total number of each part needed to assembly the project {}.'.format(i_prj)
            for k,f in columns.items():
                if f['col']>=col and k!=name:
                    f['col'] += 1

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
    # Order the references and collapse, if asked:
    # e.g. J3, J2, J1, J6 => J1, J2, J3 J6. # `collapse=False`
    # e.g. J3, J2, J1, J6 => J1-J3, J6.. # `collapse=True`
    for part in parts:
        part.collapsed_refs = ','.join( order_refs(part.refs, collapse=collapse_refs) )

    # Then, order the part references with priority ref prefix, ref num, and subpart num.
    def get_ref_key(part):
        match = re.match(PART_REF_REGEX, part.collapsed_refs)
        return [match.group('prefix'), match.group('ref_num'), match.group('subpart_num')]
    parts.sort(key=get_ref_key)

    # Add the global part data to the spreadsheet.
    for part in parts:

        # Enter part references.
        wks.write_string(row, start_col + columns['refs']['col'], part.collapsed_refs, wrk_formats['part_format'])

        # Enter more static data for the part.
        for field in list(columns.keys()):
            if columns[field]['static'] is False:
                continue
            try:
                # Fields found in the XML are lower-cased, so do the same for the column key.
                field_name = field.lower().strip()
                if field_name=='manf#':
                    try:
                        string = part.fields['manf#']
                        link  = part.fields['datasheet']
                        if re.match(DATASHEET_LINK_REGEX, link):
                            # Just put the link if is valid.
                            wks.write_url(row, start_col + columns['manf#']['col'],
                                 link, string=string)
                        else:
                            wks.write_string(row, start_col + columns[field]['col'],
                                 part.fields[field_name], wrk_formats['part_format'])
                    except KeyError:
                        wks.write_string(row, start_col + columns[field]['col'],
                                 part.fields[field_name], wrk_formats['part_format'])
                        pass
                else:
                    wks.write_string(row, start_col + columns[field]['col'],
                                 part.fields[field_name], wrk_formats['part_format'])
            except KeyError:
                pass

        # Enter total part quantity needed.
        try:
            qty = partgroup_qty(part);
            if isinstance(qty, list):
                # Multifiles BOM case, write each quantity and after,
                # in the 'qty' column the total quantity as ceil of
                # the total quantity (to ceil use a Microsoft Excel
                # compatible function.
                for i_prj in range(len(qty)):
                    wks.write(row,
                          start_col + columns['qty_prj{}'.format(i_prj)]['col'],
                          qty[i_prj].format('BoardQty{}'.format(i_prj)),
                          wrk_formats['part_format'])
                wks.write_formula(row, start_col + columns['qty']['col'],
                    '=CEILING(SUM({}:{}),1)'.format(
                        xl_rowcol_to_cell(row, start_col + columns['qty_prj0']['col']),
                        xl_rowcol_to_cell(row, start_col + columns['qty']['col']-1)
                    ),
                    wrk_formats['part_format'])
            else:
                wks.write(row, start_col + columns['qty']['col'],
                          qty.format('BoardQty'), wrk_formats['part_format'])
        except KeyError:
            pass

        # Gather the cell references for calculating minimum unit price and part availability.
        dist_unit_prices = []
        dist_qty_avail = []
        dist_qty_purchased = []
        dist_code_avail = []
        for dist in list(distributor_dict.keys()):

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

            # Get the contents of the manufacture and distributors codes.
            dist_code_avail.append(
                'ISBLANK(INDIRECT(ADDRESS(ROW(),COLUMN({})+4)))'.format(dist_data_rng))


        # If part do not have manf# code or distributor codes, color quantity cell gray.
        wks.conditional_format(
            row, start_col + columns['qty']['col'],
            row, start_col + columns['qty']['col'],
            {
                'type': 'formula',
                'criteria': '=AND(ISBLANK({g}),{d})'.format(
                    g=xl_rowcol_to_cell(row,start_col + columns['manf#']['col']), # Manf# column also have to be blank.
                    d=(','.join(dist_code_avail) if dist_code_avail else 'TRUE()')
                 ),
                'format': wrk_formats['not_manf_codes']
            }
        )

        # Enter the spreadsheet formula for calculating the minimum extended price (based on the unit price found on next formula).
        wks.write_formula(
            row, start_col + columns['ext_price']['col'],
            '=iferror({qty}*{unit_price},"")'.format(
                qty        = xl_rowcol_to_cell(row, start_col + columns['qty']['col']),
                unit_price = xl_rowcol_to_cell(row, start_col + columns['unit_price']['col'])
            ),
            wrk_formats['currency']
        )

        # If not asked to scrape, to correlate the prices and available quantities.
        if distributor_dict.keys():
            # Enter the spreadsheet formula to find this part's minimum unit price across all distributors.
            wks.write_formula(
                row, start_col + columns['unit_price']['col'],
                '=MINA({})'.format(','.join(dist_unit_prices)),
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
    # If have read multiple BOM file calculate it by `SUMPRODUCT()` of the
    # board project quantity components 'qty_prj*' by unitary price 'Unit$'.
    total_cost_col = start_col + columns['ext_price']['col']
    if isinstance(qty, list):
        unit_price_col = start_col + columns['unit_price']['col']
        unit_price_range = xl_range(PART_INFO_FIRST_ROW, unit_price_col,
                                    PART_INFO_LAST_ROW, unit_price_col)
        # Add each project board total.
        for i_prj in range(len(qty)):
            qty_col = start_col + columns['qty_prj{}'.format(i_prj)]['col']
            wks.write(total_cost_row + 3*i_prj, total_cost_col,
                      '=SUMPRODUCT({qty_range},{unit_price_range})'.format(
                            unit_price_range=unit_price_range,
                            qty_range=xl_range(PART_INFO_FIRST_ROW, qty_col,
                                PART_INFO_LAST_ROW, qty_col)),
                      wrk_formats['total_cost_currency'])
        # Add total of the spreadsheet, this can be equal or bigger than
        # than the sum of the above totals, because, in the case of partial
        # or fractional quantity of one part or subpart, the total quantity
        # column 'qty' will be the ceil of the sum of the other ones.
        total_cost_row = start_row -1 # Change the position of the total price cell.
    wks.write(total_cost_row, total_cost_col, '=SUM({sum_range})'.format(
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

    logger.log(DEBUG_OVERVIEW, '# Writing {}'.format(distributor_dict[dist]['label']))

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
            'comment': '(Unit Price) x (Purchase Qty) of each part from this distributor.\nRed -> Next price break is cheaper.\nGreen -> Cheapest supplier.'
        },
        'part_num': {
            'col': 4,
            'level': 2,
            'label': 'Cat#',
            'width': 15,
            'comment': 'Distributor-assigned catalog number for each part and link to it\'s web page (ctrl-click). Extra distributor data is shown as comment.'
        },
    }
    num_cols = len(list(columns.keys()))

    row = start_row  # Start building distributor section at this row.

    # Add label for this distributor.
    wks.merge_range(row, start_col, row, start_col + num_cols - 1,
            distributor_dict[dist]['label'].title(), wrk_formats[dist])
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
    # For check the number of BOM files read, see the length of p[?]['manf#_qty'],
    # if it is a `list()` instance, if don't, the lenth is always `1`.
    num_prj = max([len(part.fields.get('manf#_qty',[])) if isinstance(part.fields.get('manf#_qty',[]),list) else 1 for part in parts])

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
            wks.write(row, start_col + columns['part_num']['col'], dist_part_num, wrk_formats['part_format'])
        else:
            dist_part_num = 'Link' # To use as text for the link.
        try:
            # Add a comment in the 'cat#' column with extra informations gotten in the distributor web page.
            comment = '\n'.join(sorted([ k.capitalize()+SEPRTR+' '+v for k, v in part.info_dist[dist].items() if k in EXTRA_INFO_DISPLAY]))
            if comment:
                wks.write_comment(row, start_col + columns['part_num']['col'], comment)
        except:
            pass

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
                  part.qty_avail[dist], wrk_formats['part_format'])
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

            # Conditional format to show the available quantity is less than required.
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

            # Enter the formula for the extended price = purch qty * unit price.
            wks.write_formula(
                row, ext_price_col,
                '=iferror(if({purch_qty}="",{needed_qty},{purch_qty})*{unit_price},"")'.format(
                    needed_qty=xl_rowcol_to_cell(row, part_qty_col),
                    purch_qty=xl_rowcol_to_cell(row, purch_qty_col),
                    unit_price=xl_rowcol_to_cell(row, unit_price_col)),
                wrk_formats['currency'])

            if len(distributor_dict)>1: # Just use the best price highlight if more than one distributor.
                # Conditionally format the extended price cell that contains the best price.
                wks.conditional_format(row, ext_price_col, row, ext_price_col, {
                    'type': 'cell',
                    'criteria': '<=',
                    'value': xl_rowcol_to_cell(row, part_qty_col+2),
                    # This is the global data cell holding the minimum extended price for this part.
                    'format': wrk_formats['best_price']
                })
                # Conditionally format the unit price cell that contains the best price.
                wks.conditional_format(row, unit_price_col, row, unit_price_col, {
                    'type': 'cell',
                    'criteria': '<=',
                    'value': xl_rowcol_to_cell(row, part_qty_col+1),
                    # This is the global data cell holding the minimum unit price for this part.
                    'format': wrk_formats['best_price']
                })

        # Finished processing distributor data for this part.
        row += 1  # Go to next row.

    total_cost_col = start_col + columns['ext_price']['col']
    unit_cost_col = start_col + columns['unit_price']['col']
    
    # If more than one file (multi-files mode) show how many
    # parts of each BOM as found at this distributor and
    # the correspondent total price.
    if num_prj>1:
        for i_prj in range(num_prj):
            # Sum the extended prices (unit multiplied by quantity) for each file/BOM.
            qty_prj_col = part_qty_col - (num_prj - i_prj)
            row = total_cost_row + i_prj * 3
            wks.write(row, total_cost_col,
                      '=SUMPRODUCT({qty_range},{unit_price_range})'.format(
                            qty_range=xl_range(PART_INFO_FIRST_ROW, qty_prj_col,
                                            PART_INFO_LAST_ROW, qty_prj_col),
                            unit_price_range=xl_range(PART_INFO_FIRST_ROW, unit_cost_col,
                                            PART_INFO_LAST_ROW, unit_cost_col)),
                      wrk_formats['total_cost_currency'])
            # Show how many parts were found at this distributor.
            wks.write(row, total_cost_col+1,
                '=COUNTIFS({price_range},"<>",{qty_range},"<>0",{qty_range},"<>")&" of "&COUNTIFS({qty_range},"<>0",{qty_range},"<>")&" parts found"'.format(
                price_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                                     PART_INFO_LAST_ROW, total_cost_col),
                qty_range=xl_range(PART_INFO_FIRST_ROW, qty_prj_col,
                                   PART_INFO_LAST_ROW, qty_prj_col)),
                wrk_formats['found_part_pct'])
            wks.write_comment(row, total_cost_col+1, 'Number of parts found at this distributor for the project {}.'.format(i_prj))
        total_cost_row = PART_INFO_FIRST_ROW - 3 # Shift the total price in this distributor.
    
    # Sum the extended prices for all the parts to get the total cost from this distributor.
    wks.write(total_cost_row, total_cost_col, '=SUM({sum_range})'.format(
        sum_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                           PART_INFO_LAST_ROW, total_cost_col)),
              wrk_formats['total_cost_currency'])
    # Show how many parts were found at this distributor.
    wks.write(total_cost_row, total_cost_col+1,
        '=(ROWS({count_range})-COUNTBLANK({count_range}))&" of "&ROWS({count_range})&" parts found"'.format(
        #'=COUNTIF({count_range},"<>")&" of "&ROWS({count_range})&" parts found"'.format(
            count_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                                 PART_INFO_LAST_ROW, total_cost_col)),
            wrk_formats['found_part_pct'])
    wks.write_comment(total_cost_row, total_cost_col+1, 'Number of parts found at this distributor.')

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
    for position, col_tag in enumerate(distributor_dict[dist]['order_cols']):
        order_col[col_tag] = ORDER_START_COL + position  # Column for this order info.
        order_col_numeric[col_tag] = (col_tag ==
                                      'purch')  # Is this order info numeric?
        order_delimiter[col_tag] = distributor_dict[dist][
            'order_delimiter'
        ]  # Delimiter btwn order columns.
        # For the last column of order info, the delimiter is blanked.
        if position + 1 == len(distributor_dict[dist]['order_cols']):
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
        # 1) Computes the set of row index in the part data that have
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
