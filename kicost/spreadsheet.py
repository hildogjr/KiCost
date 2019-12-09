# -*- coding: utf-8 -*- 
# MIT license
#
# Copyright (C) 2019 by XESS Corporation / Hildo Guillardi Júnior
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
__author__ = 'Hildo Guillardi Júnior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

from .global_vars import * # Debug, language and default configurations.

# Python libraries.
import os
from datetime import datetime
import re # Regular expression parser.
import xlsxwriter # XLSX file interpreter.
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range, xl_range_abs
from babel import numbers # For currency presentation.

# KiCost libraries.
from . import __version__ # Version control by @xesscorp and collaborator.
from .distributors.global_vars import distributor_dict # Distributors names and definitions to use in the spreadsheet.
from .edas.tools import partgroup_qty, order_refs, PART_REF_REGEX, SUB_SEPRTR

from currency_converter import CurrencyConverter
currency_convert = CurrencyConverter().convert

__all__ = ['create_spreadsheet']


PURCHASE_DESCRIPTION_SEPRTR = SEPRTR # Purchase description separator.

# Currency format and symbol definition (placed default values here, it will be replaced by the user asked currency).
CURRENCY_ALPHA3 = DEFAULT_CURRENCY
CURRENCY_SYMBOL = 'US$'
CURRENCY_FORMAT = ''

WORKBOOK = None

# Regular expression to the link for one datasheet.
DATASHEET_LINK_REGEX = re.compile('^(http(s)?:\/\/)?(www.)?[0-9a-z\.]+\/[0-9a-z\.\/\%\-\_]+(.pdf)?$', re.IGNORECASE)

# Extra information characteristics of the components gotten in the page that will be displayed as comment in the 'cat#' column.
EXTRA_INFO_DISPLAY = ['value', 'tolerance', 'footprint', 'power', 'current', 'voltage', 'frequency', 'temp_coeff', 'manf', 'size']


# About and credit message at the end of the spreadsheet.
ABOUT_MSG='KiCost\N{REGISTERED SIGN} v.' + __version__


def create_spreadsheet(parts, prj_info, spreadsheet_filename, currency=DEFAULT_CURRENCY,
                       collapse_refs=True, supress_cat_url=True, user_fields=None, variant=None):
    '''Create a spreadsheet using the info for the parts (including their HTML trees).'''
    
    logger.log(DEBUG_OVERVIEW, 'Creating the \'{}\' spreadsheet...'.format(
                                    os.path.basename(spreadsheet_filename)) )
    
    MAX_LEN_WORKSHEET_NAME = 31 # Microsoft Excel allows a 31 characters longer
                                # string for the worksheet name, Google
                                #Spreadsheet 100 and LibreOffice Calc have no limit.
    DEFAULT_BUILD_QTY = 100  # Default value for number of boards to build.
    global WORKSHEET_NAME
    WORKSHEET_NAME = os.path.splitext(os.path.basename(spreadsheet_filename))[0] # Default name for pricing worksheet.

    global CURRENCY_SYMBOL
    global CURRENCY_FORMAT
    global CURRENCY_ALPHA3
    CURRENCY_ALPHA3 = currency.strip().upper()
    CURRENCY_SYMBOL = numbers.get_currency_symbol(
                        CURRENCY_ALPHA3, locale=DEFAULT_LANGUAGE
                        )
    CURRENCY_FORMAT = CURRENCY_SYMBOL + '#,##0.00'
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
        WRK_HDR_FORMAT = {
                'font_size': 14, 'bold': True,
                'font_color': 'white',
                'bg_color': '#303030',
                'align': 'center', 'valign': 'vcenter'
            }
        wrk_formats = {
            'global': workbook.add_format(WRK_HDR_FORMAT),
            'header': workbook.add_format({
                'font_size': 12, 'bold': True,
                'align': 'center', 'valign': 'top',
                'text_wrap': True
            }),
            'board_qty': workbook.add_format({
                'font_size': 13, 'bold': True,
                'align': 'right'
            }),
            'total_cost_label': workbook.add_format({
                'font_size': 13, 'bold': True,
                'align': 'right',
                'valign': 'vcenter'
            }),
            'unit_cost_label': workbook.add_format({
                'font_size': 13, 'bold': True,
                'align': 'right',
                'valign': 'vcenter'
            }),
            'total_cost_currency': workbook.add_format({
                'font_size': 13, 'bold': True,
                'font_color': 'red',
                'num_format': CURRENCY_FORMAT,
                'valign': 'vcenter'
            }),
            'description': workbook.add_format({
                'align': 'right'
            }),
            'unit_cost_currency': workbook.add_format({
                'font_size': 13, 'bold': True,
                'font_color': 'green',
                'num_format': CURRENCY_FORMAT,
                'valign': 'vcenter'
            }),
            'proj_info_field': workbook.add_format({
                'font_size': 13, 'bold': True,
                'align': 'right', 'valign': 'vcenter'
            }),
            'proj_info': workbook.add_format({
                'font_size': 12,
                'align': 'left', 'valign': 'vcenter'
            }),
            'part_format': workbook.add_format({
                'valign': 'vcenter',
            }),
            'part_format_obsolete': workbook.add_format({
                'valign': 'vcenter', 'bg_color': '#c000c0'
            }),
            'found_part_pct': workbook.add_format({
                'font_size': 10, 'bold': True, 'italic': True,
                'valign': 'vcenter'
            }),
            'best_price': workbook.add_format({'bg_color': '#80FF80', }),
            'not_manf_codes': workbook.add_format({'bg_color': '#AAAAAA'}),
            'not_available': workbook.add_format({'bg_color': '#FF0000', 'font_color':'white'}),
            'order_too_much': workbook.add_format({'bg_color': '#FF0000', 'font_color':'white'}),
            'order_min_qty': workbook.add_format({'bg_color': '#FFFF00'}),
            'too_few_available': workbook.add_format({'bg_color': '#FF9900', 'font_color':'black'}),
            'too_few_purchased': workbook.add_format({'bg_color': '#FFFF00'}),
            'not_stocked': workbook.add_format({'font_color': '#909090', 'align': 'right', 'valign': 'vcenter'}),
            'currency': workbook.add_format({'num_format': CURRENCY_FORMAT, 'valign': 'vcenter'}),
        }

        # Add the distinctive header format for each distributor to the `dict` of formats.
        for d in distributor_dict:
            hdr_format = WRK_HDR_FORMAT.copy()
            hdr_format.update(distributor_dict[d]['label']['format'])
            wrk_formats[d] = workbook.add_format(hdr_format)

        # Create the worksheet that holds the pricing information.
        wks = workbook.add_worksheet(WORKSHEET_NAME)
        global WORKBOOK
        WORKBOOK = workbook

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
        next_line, next_col, refs_col, qty_col, columns_global = add_globals_to_worksheet(
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
            wks.write_comment(next_row + 2, next_col - 2, 'Use the minimum extend price across distributors not taking account available quantities.')
            # Define the named cell where the total cost can be found.
            workbook.define_name('TotalCost{}'.format(i_prj_str),
                            '={wks_name}!{cell_ref}'.format(
                                wks_name="'" + WORKSHEET_NAME + "'",
                                cell_ref=xl_rowcol_to_cell(next_row + 2,
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
        web_dists = sorted([d for d in distributor_dict if distributor_dict[d]['type'] != 'local'])
        local_dists = sorted([d for d in distributor_dict if distributor_dict[d]['type'] == 'local'])
        dist_list = web_dists + local_dists

        # Load the part information from each distributor into the sheet.
        logger.log(DEBUG_OVERVIEW, 'Writing the distributor part information...')
        for dist in dist_list:
            dist_start_col = next_col
            next_col = add_dist_to_worksheet(wks, wrk_formats, columns_global,
                                            START_ROW, dist_start_col,
                                            UNIT_COST_ROW, TOTAL_COST_ROW,
                                             refs_col, qty_col, dist, parts, supress_cat_url)
            # Create a defined range for each set of distributor part data.
            workbook.define_name(
                '{}_part_data'.format(dist), '={wks_name}!{data_range}'.format(
                    wks_name="'" + WORKSHEET_NAME + "'",
                    data_range=xl_range_abs(START_ROW, dist_start_col,
                                            LAST_PART_ROW, next_col - 1)))

        # Add the KiCost package information at the end of the spreadsheet to debug
        # information at the forum and "advertising".
        wks.write(next_line+1, START_COL, ABOUT_MSG, wrk_formats['proj_info'])


def add_globals_to_worksheet(wks, wrk_formats, start_row, start_col,
                             total_cost_row, parts, user_fields, collapse_refs):
    '''Add global part data to the spreadsheet.'''

    logger.log(DEBUG_OVERVIEW, 'Writing the global part information...')

    global CURRENCY_SYMBOL
    global CURRENCY_FORMAT

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
            'level': 2,
            'label': 'Desc',
            'width': None,
            'comment': 'Description of each part.',
            'static': True,
        },
        'footprint': {
            'col': 3,
            'level': 2,
            'label': 'Footprint',
            'width': None,
            'comment': 'PCB footprint for each part.',
            'static': True,
        },
        'manf': {
            'col': 4,
            'level': 1,
            'label': 'Manf',
            'width': None,
            'comment': 'Manufacturer of each part.',
            'static': True,
        },
        'manf#': {
            'col': 5,
            'level': 1,
            'label': 'Manf#',
            'width': None,
            'comment': '''Manufacturer number for each part and link to it\'s datasheet (Ctrl-click).
Purple -> Obsolete part detected by one of the distributors.''',
            'static': True,
        },
        'qty': {
            'col': 6,
            'level': 1,
            'label': 'Qty',
            'width': None,
            'comment': '''Total number of each part needed.
Gray -> No manf# provided.
Red -> No parts available.
Orange -> Not enough parts available.
Yellow -> Parts available, but haven't purchased enough.''',
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
    def remove_col_not_exist_parts(code, table=columns):
        for part in parts:
            try:
                if part.fields[code]:
                    return
            except KeyError:
                pass
        table = remove_column(table, code) # All 'manf' are empty.
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
            desc_col = columns.get('desc', columns['value'])['col']
            # Push all existing fields to right of 'desc' over by one column.
            # Use 'value' if 'desc' was removed due not value present in the BOM.
            for id in col_ids:
                if columns[id]['col'] > desc_col:
                    columns[id]['col'] += 1
            # Insert user field in the vacated space.
            columns[user_field_id] = {
                'col': desc_col+1,
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
        #part.collapsed_refs = ','.join( order_refs(part.refs, collapse=collapse_refs) )
        part.collapsed_refs = order_refs(part.refs, collapse=collapse_refs)

    # Then, order the part references with priority ref prefix, ref num, and subpart num.
    def get_ref_key(part):
        match = re.match(PART_REF_REGEX, part.collapsed_refs)
        return [match.group('prefix'), match.group('ref_num'), match.group('subpart_num')]
    parts.sort(key=get_ref_key)

    # Add the global part data to the spreadsheet.
    used_currencies = []
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
                    string = part.fields.get('manf#')
                    link  = part.fields.get('datasheet')
                    if not link:
                        try:
                            # Use the the datasheet link got in the distributor if not
                            # available any in the BOM / schematic.
                            link = part.datasheet
                        except:
                            pass
                    try:
                        lifecycle = part.lifecycle
                        if lifecycle=='obsolete':
                            cell_format = wrk_formats['part_format_obsolete']
                        else:
                            cell_format = wrk_formats['part_format']
                    except:
                        cell_format = wrk_formats['part_format']
                        pass
                    if link and re.match(DATASHEET_LINK_REGEX, link):
                        # Just put the link if is a valid format.
                        wks.write_url(row, start_col + columns['manf#']['col'],
                             link, string=string, cell_format=cell_format)
                    else:
                        wks.write_string(row, start_col + columns[field]['col'],
                             part.fields[field_name], cell_format)
                else:
                    if field_name=='footprint':
                        ##TODO add future dependence of "electro-grammar" (https://github.com/kitspace/electro-grammar)
                        field_value_footprint = re.findall('\:(.*)', part.fields[field_name])
                        if field_value_footprint:
                            field_value = field_value_footprint[0]
                    else:
                        field_value = part.fields[field_name]
                    wks.write_string(row, start_col + columns[field]['col'],
                                 field_value, wrk_formats['part_format'])
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
        dist_ext_prices = []
        for dist in list(distributor_dict.keys()):

            # Get the currencies used among all distributors.
            used_currencies.append(part.currency[dist])

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

            # Get the contents of the manufacture and distributors codes.
            dist_ext_prices.append(
                'INDIRECT(ADDRESS(ROW(),COLUMN({})+3))'.format(dist_data_rng))

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

    # Add the total purchase and others purchase informations.
    if distributor_dict.keys():
        next_line = row + 1
        wks.write(next_line, start_col + columns['unit_price']['col'],
                      'Total Purchase:', wrk_formats['total_cost_label'])
        wks.write_comment(next_line, start_col + columns['unit_price']['col'],
                      'This is the total of your cart across all distributors.')
        wks.write(next_line, start_col + columns['ext_price']['col'],
                  '=SUM({})'.format(','.join(dist_ext_prices)),
              wrk_formats['total_cost_currency'])
        # Purchase general description, it may be used to distinguish carts of different projects.
        next_line = next_line + 1
        wks.write(next_line, start_col + columns['unit_price']['col'],
                      'Purchase description:', wrk_formats['description'])
        wks.write_comment(next_line, start_col + columns['unit_price']['col'],
                      'This description will be added to all purchased parts label and may be used to distinguish the component of different projects.')
        WORKBOOK.define_name('PURCHASE_DESCRIPTION',
            '={wks_name}!{cell_ref}'.format(
                wks_name="'" + WORKSHEET_NAME + "'",
                cell_ref=xl_rowcol_to_cell(next_line, columns['ext_price']['col'],
                                       row_abs=True, col_abs=True)))

    # Get the actual currency rate to use.
    next_line = row + 1
    used_currencies = list(set(used_currencies))
    logger.log(DEBUG_OVERVIEW, 'Getting distributor currency convertion rate {} to {}...', used_currencies, CURRENCY_ALPHA3)
    if len(used_currencies)>1:
        if CURRENCY_ALPHA3 in used_currencies:
            used_currencies.remove(CURRENCY_ALPHA3)
        wks.write(next_line, start_col + columns['value']['col'],
                    'Used currency rates:', wrk_formats['description'])
        next_line = next_line + 1
    for used_currency in used_currencies:
        if used_currency!=CURRENCY_ALPHA3:
            wks.write(next_line, start_col + columns['value']['col'],
                      '{c}({c_s})/{d}({d_s}):'.format(c=CURRENCY_ALPHA3, d=used_currency, c_s=CURRENCY_SYMBOL,
                                    d_s=numbers.get_currency_symbol(used_currency, locale=DEFAULT_LANGUAGE)
                                  ),
                        wrk_formats['description']
                      )
            WORKBOOK.define_name('{c}_{d}'.format(c=CURRENCY_ALPHA3, d=used_currency),
                '={wks_name}!{cell_ref}'.format(
                    wks_name="'" + WORKSHEET_NAME + "'",
                    cell_ref=xl_rowcol_to_cell(next_line, columns['value']['col'] + 1,
                                           row_abs=True, col_abs=True)))
            wks.write(next_line, columns['value']['col'] + 1,
                        currency_convert(1, used_currency, CURRENCY_ALPHA3)
                      )
            next_line = next_line + 1

    # Return column following the globals so we know where to start next set of cells.
    # Also return the columns where the references and quantity needed of each part is stored.
    return next_line, start_col + num_cols, start_col + columns['refs']['col'], start_col + columns['qty']['col'], columns


def add_dist_to_worksheet(wks, wrk_formats, columns_global, start_row, start_col,
                          unit_cost_row, total_cost_row, part_ref_col, part_qty_col,
                          dist, parts, supress_cat_url=True):
    '''Add distributor-specific part data to the spreadsheet.'''

    logger.log(DEBUG_OVERVIEW, '# Writing {}'.format(distributor_dict[dist]['label']))

    global CURRENCY_ALPHA3

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
            'comment': 'Purchase quantity of each part from this distributor.\nYellow -> This part have a minimum purchase quantity bigger than 1 (check the price breaks).\nRed -> Purchasing more than the available quantity.'
        },
        'unit_price': {
            'col': 2,
            'level': 2,
            'label': 'Unit$',
            'width': None,
            'comment': 'Unit price of each part from this distributor.\nGreen -> lowest price across distributors.'
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
    if not supress_cat_url:
        # Add a extra column to the hiperlink.
        columns.update({'link': {
                            'col': 5,
                            'level': 2,
                            'label': 'URL',
                            'width': 15,
                            'comment': 'Distributor catalog link (ctrl-click).'
                        }})
        columns['part_num']['comment'] = 'Distributor-assigned catalog number for each part. Extra distributor data is shown as comment.'
    num_cols = len(list(columns.keys()))

    row = start_row  # Start building distributor section at this row.

    # Add label for this distributor.
    wks.merge_range(row, start_col, row, start_col + num_cols - 1,
            #distributor_dict[dist]['label']['name'].title(),
            distributor_dict[dist]['label']['name'],
            wrk_formats[dist])
    #if distributor_dict[dist]['type']!='local':
    #    wks.write_url(row, start_col,
    #        distributor_dict[dist]['label']['url'], wrk_formats[dist],
    #        distributor_dict[dist]['label']['name'].title())
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

        dist_part_num = part.part_num[dist] # Get the distributor part number.
        price_tiers = part.price_tiers[dist] # Extract price tiers from distributor HTML page tree.
        dist_currency =  part.currency[dist] # Extract currency used by the distributor.

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
            if supress_cat_url:
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
            if supress_cat_url:
                wks.write_url(row, start_col + columns['part_num']['col'],
                    part.url[dist], string=dist_part_num)
            else:
                wks.write_url(row, start_col + columns['link']['col'], part.url[dist])

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
                minimum_order_qty = min_qty # Update the minimum order quantity.
                if min_qty > 1:
                    price_tiers[1] = price_tiers[min_qty] # Set unit price to price of lowest available quantity.
            except ValueError:  # This happens if the price tier list is empty.
                pass
            price_tiers[0] = 0.00  # Enter quantity-zero pricing so `LOOKUP` works correctly in the spreadsheet.

            # Sort the tiers based on quantities and turn them into lists of strings.
            qtys = sorted(price_tiers.keys())

            avail_qty_col = start_col + columns['avail']['col']
            purch_qty_col = start_col + columns['purch']['col']
            unit_price_col = start_col + columns['unit_price']['col']
            ext_price_col = start_col + columns['ext_price']['col']

            # Enter a spreadsheet lookup function that determines the unit price based on the needed quantity
            # or the purchased quantity (if that is non-zero).
            if dist_currency==CURRENCY_ALPHA3:
                wks.write_formula(
                    row, unit_price_col,
                    '=iferror(lookup(if({purch_qty}="",{needed_qty},{purch_qty}),{{{qtys}}},{{{prices}}}),"")'.format(
                        needed_qty=xl_rowcol_to_cell(row, part_qty_col),
                        purch_qty=xl_rowcol_to_cell(row, purch_qty_col),
                        qtys=','.join([str(q) for q in qtys]),
                        prices=','.join([str(price_tiers[q]) for q in qtys])),
                        wrk_formats['currency'])
            else:
                wks.write_formula(
                    row, unit_price_col,
                    '=iferror({rate}*lookup(if({purch_qty}="",{needed_qty},{purch_qty}),{{{qtys}}},{{{prices}}}),"")'.format(
                        rate='{c}_{d}'.format(c=CURRENCY_ALPHA3, d=dist_currency), # Currency rate used to this distributor.
                        needed_qty=xl_rowcol_to_cell(row, part_qty_col),
                        purch_qty=xl_rowcol_to_cell(row, purch_qty_col),
                        qtys=','.join([str(q) for q in qtys]),
                        prices=','.join([str(price_tiers[q]) for q in qtys])),
                        wrk_formats['currency'])

            # Add a comment to the cell showing the qty/price breaks.
            dist_currency_symbol = numbers.get_currency_symbol(dist_currency, locale=DEFAULT_LANGUAGE)
            price_break_info = 'Qty/Price Breaks ({c}):\n  Qty  -  Unit{s}  -  Ext{s}\n================'.format(c=dist_currency, s=dist_currency_symbol)
            for q in qtys[1 if minimum_order_qty==1 else 2:]:
                # Skip the unity quantity for the tip balloon if it not allow to purchase in the distributor.
                price = price_tiers[q]
                price_break_info += '\n{:>6d} {:>7s} {:>10s}'.format( q,
                    numbers.format_currency(price, dist_currency, locale=DEFAULT_LANGUAGE),
                    numbers.format_currency(price*q, dist_currency, locale=DEFAULT_LANGUAGE))
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

            # Conditional format to show that the part have a minimum order quantity not respected.
            if minimum_order_qty>1:
                wks.conditional_format(
                    row, start_col + columns['purch']['col'], 
                    row, start_col + columns['purch']['col'],
                    {
                        'type': 'formula',
                        'criteria': '=AND({q}>0,{q}<{moq})'.format(
                            q=xl_rowcol_to_cell(row, start_col + columns['purch']['col']),
                            moq=minimum_order_qty
                        ),
                        'format': wrk_formats['order_min_qty']
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
    dist_cat_col = start_col + columns['part_num']['col']
    
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
            wks.write(row, dist_cat_col,
                '=COUNTIFS({price_range},"<>",{qty_range},"<>0",{qty_range},"<>")&" of "&COUNTIFS({qty_range},"<>0",{qty_range},"<>")&" parts found"'.format(
                price_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                                     PART_INFO_LAST_ROW, total_cost_col),
                qty_range=xl_range(PART_INFO_FIRST_ROW, qty_prj_col,
                                   PART_INFO_LAST_ROW, qty_prj_col)),
                wrk_formats['found_part_pct'])
            wks.write_comment(row, dist_cat_col, 'Number of parts found at this distributor for the project {}.'.format(i_prj))
        total_cost_row = PART_INFO_FIRST_ROW - 3 # Shift the total price in this distributor.
    
    # Sum the extended prices for all the parts to get the total cost from this distributor.
    wks.write(total_cost_row, total_cost_col, '=SUM({sum_range})'.format(
        sum_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                           PART_INFO_LAST_ROW, total_cost_col)),
              wrk_formats['total_cost_currency'])
    # Show how many parts were found at this distributor.
    wks.write(total_cost_row, dist_cat_col,
        '=(COUNTA({count_range})&" of "&ROWS({count_range})&" parts found"'.format(
        #'=COUNTIF({count_range},"<>")&" of "&ROWS({count_range})&" parts found"'.format(
            count_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                                 PART_INFO_LAST_ROW, total_cost_col)),
            wrk_formats['found_part_pct'])
    wks.write_comment(total_cost_row, dist_cat_col, 'Number of parts found at this distributor.')

    # Add list of part numbers and purchase quantities for ordering from this distributor.
    ORDER_START_COL = start_col + 1
    ORDER_FIRST_ROW = PART_INFO_LAST_ROW + 3
    ORDER_LAST_ROW = ORDER_FIRST_ROW + num_parts - 1

    # Write the header and how many parts are being purchased.
    purch_qty_col = start_col + columns['purch']['col']
    ext_price_col = start_col + columns['ext_price']['col']
    ORDER_HEADER =  PART_INFO_LAST_ROW + 2
    wks.write_formula( # Expended many in this distributor.
        ORDER_HEADER, ext_price_col,
        '=SUMIF({count_range},">0",{price_range})'.format(
            count_range=xl_range(PART_INFO_FIRST_ROW, purch_qty_col,
                                 PART_INFO_LAST_ROW, purch_qty_col),
            price_range=xl_range(PART_INFO_FIRST_ROW, ext_price_col,
                                 PART_INFO_LAST_ROW, ext_price_col),
        ),
        wrk_formats['total_cost_currency']
    )
    wks.write_formula( # Quantity of purchased part in this distributor.
        ORDER_HEADER, purch_qty_col,
        '=IFERROR(IF(OR({count_range}),COUNTIFS({count_range},">0",{count_range_price},"<>")&" of "&(ROWS({count_range_price})-COUNTBLANK({count_range_price}))&" parts purchased",""),"")'.format(
            count_range=xl_range(PART_INFO_FIRST_ROW, purch_qty_col,
                                 PART_INFO_LAST_ROW, purch_qty_col),
            count_range_price=xl_range(PART_INFO_FIRST_ROW, ext_price_col,
                                 PART_INFO_LAST_ROW, ext_price_col)
        ),
        wrk_formats['found_part_pct']
    )
    wks.write_comment(ORDER_HEADER, purch_qty_col,
        'Copy the information below to the BOM import page of the distributor web site.')


    # Write the spreadsheet code to multiple lines to create the purchase codes to
    # be used in this current distributor.
    try:
        cols = distributor_dict[dist]['order']['cols']
    except KeyError:
        return start_col + num_cols # If not created the distributor definition, jump this final code part.

    # Create the header of the purchase codes, if present the definition.
    try:
        wks.write_formula(ORDER_FIRST_ROW, ORDER_START_COL,
                         '=IFERROR(IF(COUNTIFS({count_range},">0",{count_range_price},"<>")>0,"{header}",""),"")'.format(
                            count_range=xl_range(PART_INFO_FIRST_ROW, purch_qty_col,
                                PART_INFO_LAST_ROW, purch_qty_col),
                            count_range_price=xl_range(PART_INFO_FIRST_ROW, ext_price_col,
                                PART_INFO_LAST_ROW, ext_price_col),
                            header=distributor_dict[dist]['order']['header'],
                         ),
                         wrk_formats['found_part_pct']
        )
        try:
            wks.write_comment(ORDER_FIRST_ROW, ORDER_START_COL, distributor_dict[dist]['order']['info'])
        except KeyError:
            pass
        ORDER_FIRST_ROW = ORDER_FIRST_ROW + 1 # Push all the code list one row.
        ORDER_LAST_ROW = ORDER_LAST_ROW + 1
    except KeyError:
        pass

    if not('purch' in cols and ('part_num' in cols or 'manf#' in cols)):
        logger.log(DEBUG_OVERVIEW, "Purchase list codes for {d} will not be generated.".format(
                            d=distributor_dict[dist]['name']
                        ))
    else:
        # This script enters a function into a spreadsheet cell that
        # prints the information found in info_col into the order_col column
        # of the order.
        # This very complicated spreadsheet function does the following:
        # 1) Computes the set of row index in the part data that have
        #    non-empty cells in sel_range1 and sel_range2. (Innermost
        #    nested IF and ROW commands.) sel_range1 and sel_range2 are
        #    the part's catalog number and purchase quantity.
        # 2) Selects the k'th smallest of the row index where k is the
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
        order_func = 'IFERROR(CONCATENATE({}),"")'
        order_info_func_model = '''
                        INDEX(
                            {get_range},
                            SMALL(
                                IF( ISNUMBER({qty}),
                                    IF( {qty} > 0,
                                        IF( {code} <> "",
                                            ROW({qty}) - MIN(ROW({qty})) + 1
                                        )
                                    )
                                ),
                                ROW()-ROW({order_first_row})+1
                            )
                        )
        '''
        order_info_func_model = re.sub('[\s\n]', '', order_info_func_model) # Strip all the whitespace from the function string.

        # Create the line order by the fields specified by each distributor.
        delimier = ',"' + distributor_dict[dist]['order']['delimiter'] + '",' # Function delimiter plus distributor code delimiter.
        order_part_info = []
        for col in cols:
            # Deal with conversion and string replace necessary to the correct distributors
            # code understanding.
            if col=='purch':
                # Add text conversion if is a numeric cell.
                order_part_info.append('TEXT({},"##0")'.format(order_info_func_model))
            elif col not in ['part_num', 'purch', 'manf#']:
                # All comment and description columns (that are not quantity and catalogue code)
                # should respect the allowed characters. These are text informative columns.
                #if col=='refs':
                #    # If 'refs' column an additional rule to remove the subpart counter.
                #    order_info_func_parcial = 'REGEX({f},"\{c}\d+","","g")'.format(f=order_info_func_model,c=SUB_SEPRTR)
                #    This is not supported by Microsoft Excel. ## TODO
                #else:
                order_info_func_parcial = order_info_func_model
                if 'not_allowed_char' in distributor_dict[dist]['order'] and 'replace_by_char' in distributor_dict[dist]['order']:
                    for c in range(len(distributor_dict[dist]['order']['not_allowed_char'])):
                        not_allowed_char = distributor_dict[dist]['order']['not_allowed_char'][c]
                        if len(distributor_dict[dist]['order']['replace_by_char'])>1:
                            replace_by_char = distributor_dict[dist]['order']['replace_by_char'][c]
                        else:
                            replace_by_char = distributor_dict[dist]['order']['replace_by_char'][0]
                        order_info_func_parcial = 'SUBSTITUTE({t},"{o}","{n}")'.format(
                                t=order_info_func_parcial,
                                o=not_allowed_char,
                                n=replace_by_char)
                order_part_info.append(order_info_func_parcial)
            else:
                order_part_info.append(order_info_func_model)
            # Look for the `col` name into the distributor spreadsheet part
            # with don't find, it belongs to the global part.
            if col in columns:
                info_range = start_col + columns[col]['col']
            elif col in columns_global:
                info_range = columns_global[col]['col']
            else:
                info_range = ""
                logger.warning("Not valid field `{f}` for purchase list at {d}.".format(
                            f=col,
                            d=distributor_dict[dist]['name']
                        ))
            info_range =xl_range(PART_INFO_FIRST_ROW, info_range,
                                 PART_INFO_LAST_ROW, info_range)
            # If the correspondent information is some description, it is allow to add the general
            # purchase designator. it is placed inside the "not allow characters" restriction.
            if col not in ['part_num', 'purch', 'manf#']:
                info_range = 'IF(PURCHASE_DESCRIPTION<>"",PURCHASE_DESCRIPTION&"{}","")'.format(PURCHASE_DESCRIPTION_SEPRTR)+ '&' + info_range
            # Create the part of formula that refers with one specific information.
            order_part_info[-1] = order_part_info[-1].format(
                        get_range=info_range,
                        qty='{qty}', # keep all other for future replacement.
                        code='{code}',
                        order_first_row='{order_first_row}')
        # If already have some information, add the delimiter for
        # Microsoft Excel/LibreOffice Calc function.
        order_func = order_func.format( delimier.join(order_part_info) )

        # These are the columns where the part catalog numbers and purchase quantities can be found.
        if 'part_num' in cols:
            purchase_code = start_col + columns['part_num']['col']
        elif 'manf#' in cols:
            purchase_code = start_col + columns_global['manf#']['col']
        else:
            purchase_code = ""
            logger.warning("Not valid  quantity/code field `{f}` for purchase list at {d}.".format(
                        f=col,
                        d=distributor_dict[dist]['name']
                    ))
        purchase_code = xl_range(PART_INFO_FIRST_ROW, purchase_code,
                                 PART_INFO_LAST_ROW, purchase_code)
        purchase_qty = start_col + columns['purch']['col']
        purchase_qty = xl_range(PART_INFO_FIRST_ROW, purchase_qty,
                                PART_INFO_LAST_ROW, purchase_qty)
        # Fill the formula with the control parameters.
        order_func = order_func.format(
                        order_first_row=xl_rowcol_to_cell(ORDER_FIRST_ROW, 0, row_abs=True),
                        code=purchase_code,
                        qty=purchase_qty
                    )
        # Now write the order_func into every row of the order in the given column.
        dist_col = start_col + columns['unit_price']['col']
        info_col = dist_col
        for r in range(ORDER_FIRST_ROW, ORDER_LAST_ROW + 1):
            wks.write_array_formula(
                xl_range(r, ORDER_START_COL, r, ORDER_START_COL), '{{={f}}}'.format(f=order_func))

    return start_col + num_cols # Return column following the globals so we know where to start next set of cells.


def remove_column(table, name):
    '''Remove a speficied columns from a create table.'''
    for h in table:
        if table[h]['col']>table[name]['col']:
            table[h]['col'] -= 1
    del table[name]
    return table