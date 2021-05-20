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

# Debug, language and default configurations.
from .global_vars import (SEPRTR, DEFAULT_CURRENCY, DEFAULT_LANGUAGE, DEBUG_OVERVIEW, DEBUG_DETAILED, DEF_MAX_COLUMN_W, get_logger, W_NOPURCH, W_NOQTY,
                          ERR_FIELDS, KiCostError)

# Python libraries.
import os
from datetime import datetime
from copy import deepcopy
from math import ceil
from textwrap import wrap
import re  # Regular expression parser.
import xlsxwriter  # XLSX file interpreter.
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range_abs
from validators import url as validate_url  # URL validator.

# KiCost libraries.
from .version import __version__  # Version control by @xesscorp and collaborator.
from .distributors import get_distributor_info, ORDER_COL_USERFIELDS
from .edas.tools import partgroup_qty, order_refs, PART_REF_REGEX

from .currency_converter import CurrencyConverter, get_currency_symbol, format_currency
currency_convert = CurrencyConverter().convert

__all__ = ['create_spreadsheet', 'create_worksheet', 'Spreadsheet']


# This function is not the same for all xlsxwriter version, generating uncosistent outputs
def xl_range(first_row, first_col, last_row, last_col):
    range1 = xl_rowcol_to_cell(first_row, first_col)
    range2 = xl_rowcol_to_cell(last_row, last_col)
    if range1 == range2:
        return range1
    return range1 + ':' + range2


# This class is used to configure the spreadsheet creation.
# Settings can be used inside KiCost or from any tool using KiCost as a module.
# It was originally created to control the spreadsheet details from KiBot.
class Spreadsheet(object):
    ''' A class to hold the spreadsheet generation settings '''
    # Note: upper case members are static. Can be read by the objects, but shouldn't be modfified by the objects.
    # They work as configuration parameters to fine tune the spreadsheet content and aspect.
    #
    # Microsoft Excel allows a 31 characters longer string for the worksheet name, Google
    # Spreadsheet 100 and LibreOffice Calc have no limit.
    MAX_LEN_WORKSHEET_NAME = 31
    # Try to make columns wide enough to make their text readable
    # If they are bigger than MAX_COL_WIDTH try to make them taller
    ADJUST_ROW_AND_COL_SIZE = True
    # Limit the cells width to this size
    MAX_COL_WIDTH = DEF_MAX_COLUMN_W
    # Don't adjust bellow this width
    MIN_COL_WIDTH = 6
    # Constant used to fine tune the cell adjust
    # Values bigger than 1.0 makes columns wider, also affects the row heights
    ADJUST_WEIGHT = 1.0
    # References separator
    PART_NSEQ_SEPRTR = ','
    # Include project/s information
    INCLUDE_PRJ_INFO = True
    # How many rows has the project information
    PRJ_INFO_ROWS = 3
    # First row for the project information
    PRJ_INFO_START = 0
    # Add date to the top and/or bottom
    ADD_DATE_TOP = True
    ADD_DATE_BOTTOM = False
    DATE_FIELD_LABEL = '$ date:'
    # Default value for number of boards to build.
    DEFAULT_BUILD_QTY = 100
    # About and credit message at the end of the spreadsheet.
    ABOUT_MSG = 'KiCost\N{REGISTERED SIGN} v.' + __version__
    # Try to group references as ranges
    COLLAPSE_REFS = True
    # Don't add the link column
    SUPPRESS_CAT_URL = True
    # Columns to add to the global section
    USER_FIELDS = []
    # List of selected distributors
    DISTRIBUTORS = []
    # Sort the distributors alphabetically.
    # But first the web distributors and then the local ones
    SORT_DISTRIBUTORS = True
    # Columns used for the global section
    GLOBAL_COLUMNS = {
        'refs': {
            'col': 0,
            'level': 0,  # Outline level (or hierarchy level) for this column.
            'label': 'Refs',
            'width': None,  # Column width (default in this case).
            'comment': 'Schematic identifier for each part.',
            'static': False,  # Non static columns are "computed"
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
            'comment': 'Manufacturer number for each part and link to it\'s datasheet (Ctrl-click).\n'
                       'Purple -> Obsolete part detected by one of the distributors.',
            'static': True,
        },
        'qty': {
            'col': 6,
            'level': 1,
            'label': 'Qty',
            'width': None,
            'comment': "Total number of each part needed.\n"
                       "Gray -> No manf# provided.\n"
                       "Red -> No parts available.\n"
                       "Orange -> Not enough parts available.\n"
                       "Yellow -> Parts available, but haven't purchased enough.",
            'static': False,
        },
        'unit_price': {
            'col': 7,
            'level': 0,
            'label': 'Unit$',
            'width': 9,  # Displays up to $99,999.999 without "###".
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
    DISTRIBUTOR_COLUMNS = {
        'avail': {
            'col': 0,
            # column offset within this distributor range of the worksheet.
            'level': 1,  # Outline level (or hierarchy level) for this column.
            'label': 'Avail',  # Column header label.
            'width': None,  # Column width (default in this case).
            'comment': 'Available quantity of each part at the distributor.\n'
                       'Red -> No quantity available.\n'
                       'Orange -> Too little quantity available.'
        },
        'purch': {
            'col': 1,
            'level': 2,
            'label': 'Purch',
            'width': None,
            'comment': 'Purchase quantity of each part from this distributor.\nYellow -> This part have a minimum purchase quantity bigger than 1'
                       ' (check the price breaks).\nRed -> Purchasing more than the available quantity.'
        },
        'unit_price': {
            'col': 2,
            'level': 2,
            'label': 'Unit$',
            'width': 9,  # Displays up to $99,999.999 without "###".
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
    # Cell formats
    WRK_FORMATS = {
        'global': {'font_size': 14, 'bold': True, 'font_color': 'white', 'bg_color': '#303030', 'align': 'center', 'valign': 'vcenter'},
        'header': {'font_size': 12, 'bold': True, 'align': 'center', 'valign': 'top'},
        'board_qty': {'font_size': 13, 'bold': True, 'align': 'right'},
        'total_cost_label': {'font_size': 13, 'bold': True, 'align': 'right', 'valign': 'vcenter'},
        'unit_cost_label': {'font_size': 13, 'bold': True, 'align': 'right', 'valign': 'vcenter'},
        'total_cost_currency': {'font_size': 13, 'bold': True, 'font_color': 'red', 'valign': 'vcenter'},
        'description': {'align': 'right'},
        'unit_cost_currency': {'font_size': 13, 'bold': True, 'font_color': 'green', 'valign': 'vcenter'},
        'proj_info_field': {'font_size': 13, 'bold': True, 'align': 'right', 'valign': 'vcenter'},
        'proj_info': {'font_size': 12, 'align': 'left', 'valign': 'vcenter'},
        'about_msg': {'font_size': 12, 'align': 'left', 'valign': 'vcenter'},
        'part_format': {'valign': 'vcenter'},
        'part_format_obsolete': {'valign': 'vcenter', 'bg_color': '#c000c0'},
        'found_part_pct': {'font_size': 10, 'bold': True, 'italic': True, 'valign': 'vcenter'},
        'best_price': {'bg_color': '#80FF80', },
        'not_manf_codes': {'bg_color': '#AAAAAA'},
        'not_available': {'bg_color': '#FF0000', 'font_color': 'white'},
        'order_too_much': {'bg_color': '#FF0000', 'font_color': 'white'},
        'order_min_qty': {'bg_color': '#FFFF00'},
        'too_few_available': {'bg_color': '#FF9900', 'font_color': 'black'},
        'too_few_purchased': {'bg_color': '#FFFF00'},
        'not_stocked': {'font_color': '#909090', 'align': 'right', 'valign': 'vcenter'},
        'currency': {'valign': 'vcenter'},
        'currency_unit': {'valign': 'vcenter'},
    }

    def __init__(self, workbook, worksheet_name, prj_info, currency=DEFAULT_CURRENCY):
        super(Spreadsheet, self).__init__()
        self.workbook = workbook
        self.worksheet_name = worksheet_name
        self.purchase_description_seprtr = SEPRTR  # Purchase description separator.
        self.prj_info = prj_info
        self.START_ROW = self.PRJ_INFO_START+1+self.PRJ_INFO_ROWS*len(prj_info)
        # Currency format and symbol definition
        self.set_currency(currency)
        # Extra information characteristics of the components gotten in the page that will be displayed as comment in the 'cat#' column.
        self.extra_info_display = ['value', 'tolerance', 'footprint', 'power', 'current', 'voltage', 'frequency', 'temp_coeff', 'manf', 'size']
        # Create the worksheet that holds the pricing information.
        self.wks = workbook.add_worksheet(worksheet_name)
        # Data to performe cell size adjust
        self.col_widths = {}
        self.row_heights = {}
        self.col_levels = {}

    def set_currency(self, currency):
        if currency:
            self.currency_alpha3 = currency.strip().upper()
            self.currency_symbol = get_currency_symbol(self.currency_alpha3, locale=DEFAULT_LANGUAGE)
            self.currency_format = self.currency_symbol + '#,##0.00'
            # Unit cost can be very small for pasive components, we use one extra digit
            self.currency_format_unit = self.currency_format + '0'
        else:
            self.currency_alpha3 = DEFAULT_CURRENCY
            self.currency_symbol = 'US$'
            self.currency_format = self.currency_format_unit = ''

    def write_string(self, row, col, text, format):
        """ worksheet.write_string wrapper to keep track of the string sizes. """
        self.wks.write_string(row, col, text, self.wrk_formats[format])
        self.compute_cell_size(row, col, text, format)

    def write_url(self, row, col, url, cell_format=None, string=None, tip=None):
        """ worksheet.write_url wrapper to keep track of the string sizes. """
        format = cell_format if cell_format is None else self.wrk_formats[cell_format]
        self.wks.write_url(row, col, url, cell_format=format, string=string, tip=tip)
        text = string if string is not None else url
        self.compute_cell_size(row, col, text, cell_format)

    def compute_cell_size(self, row, col, text, format):
        """ Compute cell size adjusts """
        # Compute a scale factor
        multiplier = 1.0
        if format:
            format = self.WRK_FORMATS[format]
            size = format.get('font_size', 11)
            bold = format.get('bold', False)
            # Try to adjust according to font size and weigth
            multiplier += (size - 11) * 0.08 + (0.1 if bold else 0.0)
        multiplier *= self.ADJUST_WEIGHT
        # Adjust the sizes
        l_text = ceil(len(text) * multiplier)
        if l_text > Spreadsheet.MIN_COL_WIDTH:
            cur_l = self.col_widths.get(col, Spreadsheet.MIN_COL_WIDTH)
            self.col_widths[col] = min(max(l_text, cur_l), Spreadsheet.MAX_COL_WIDTH)
            if l_text > Spreadsheet.MAX_COL_WIDTH:
                h = len(wrap(text, Spreadsheet.MAX_COL_WIDTH))
                cur_h = self.row_heights.get(row, 1)
                if h > cur_h:
                    self.row_heights[row] = h

    def adjust_row_and_col_sizes(self, logger):
        """ Adjust the column and row sizes using the values computed by compute_cell_size """
        logger.log(DEBUG_OVERVIEW, 'Adjusting cell sizes')
        logger.log(DEBUG_DETAILED, 'Column adjusts: ' + str(self.col_widths))
        logger.log(DEBUG_DETAILED, 'Row adjusts: ' + str(self.row_heights))
        logger.log(DEBUG_DETAILED, 'Levels: ' + str(self.col_levels))
        for i, width in self.col_widths.items():
            level = self.col_levels.get(i, 0)
            if level:
                self.wks.set_column(i, i, width + 1, None, {'level': level})
            else:
                self.wks.set_column(i, i, width + 1)
        # Set the level for the columns that we didn't adjust
        for i, level in self.col_levels.items():
            if i not in self.col_widths:
                self.wks.set_column(i, i, None, None, {'level': level})
        for r, height in self.row_heights.items():
            self.wks.set_row(r, 15.0 * height * self.ADJUST_WEIGHT)

    def set_column(self, col, width, level):
        if self.ADJUST_ROW_AND_COL_SIZE:
            # Add it to the computation
            if width is not None:
                self.col_widths[col] = max(self.col_widths.get(col, 0), width)
            if level:
                self.col_levels[col] = level
        else:
            # Do it now
            self.wks.set_column(col, col, width, None, {'level': level})

    def get_for_sheet(self, text):
        """ Returns a name qualified for this sheet """
        return "'{}'!{}".format(self.worksheet_name, text)

    def get_ref(self, row, col):
        """ Returns an absolute reference to row/col on this sheet """
        return '=' + self.get_for_sheet(xl_rowcol_to_cell(row, col, row_abs=True, col_abs=True))

    def get_range(self, row1, col1, row2, col2):
        """ Returns an absolute reference to a range on this sheet """
        return '=' + self.get_for_sheet(xl_range_abs(row1, col1, row2, col2))

    def define_name_ref(self, name, row, col):
        """ Define a local variable assigned to an absolute position in the sheet """
        self.workbook.define_name(self.get_for_sheet(name), self.get_ref(row, col))

    def define_name_range(self, name, row1, col1, row2, col2):
        """ Define a local variable assigned to an absolute range in the sheet """
        self.workbook.define_name(self.get_for_sheet(name), self.get_range(row1, col1, row2, col2))

    def add_date(self, row, col):
        self.wks.write(row, col, self.DATE_FIELD_LABEL, self.wrk_formats['proj_info_field'])
        self.wks.write(row, col+1, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.wrk_formats['proj_info'])


def create_spreadsheet(parts, prj_info, spreadsheet_filename, dist_list, currency=DEFAULT_CURRENCY,
                       collapse_refs=True, suppress_cat_url=True, user_fields=[], variant=' ', max_column_width=DEF_MAX_COLUMN_W):
    '''Create a spreadsheet using the info for the parts (including their HTML trees).'''
    basename = os.path.basename(spreadsheet_filename)
    logger = get_logger()
    logger.log(DEBUG_OVERVIEW, 'Creating the \'{}\' spreadsheet...'.format(basename))
    # Adjust the name of the work_sheet (add variant and limit len)
    worksheet_name = os.path.splitext(basename)[0]  # Default name for pricing worksheet.
    variant = variant.strip()
    if len(variant) > 0:
        # Append an indication of the variant to the worksheet title.
        # Remove any special characters that might be illegal in a
        # worksheet name since the variant might be a regular expression.
        # Fix the maximum worksheet name, priorize the variant string cutting
        # the board project.
        variant = re.sub(r'[\[\]\\\/\|\?\*\:\(\)]', '_', variant[:(Spreadsheet.MAX_LEN_WORKSHEET_NAME)])
        worksheet_name += '.'
        worksheet_name = worksheet_name[:(Spreadsheet.MAX_LEN_WORKSHEET_NAME-len(variant))]
        worksheet_name += variant
    else:
        worksheet_name = worksheet_name[:Spreadsheet.MAX_LEN_WORKSHEET_NAME]
    # Create spreadsheet file.
    with xlsxwriter.Workbook(spreadsheet_filename) as workbook:
        Spreadsheet.COLLAPSE_REFS = collapse_refs
        Spreadsheet.SUPPRESS_CAT_URL = suppress_cat_url
        Spreadsheet.USER_FIELDS = user_fields
        Spreadsheet.DISTRIBUTORS = dist_list
        if max_column_width:
            Spreadsheet.ADJUST_ROW_AND_COL_SIZE = True
            Spreadsheet.MAX_COL_WIDTH = max_column_width
        else:
            Spreadsheet.ADJUST_ROW_AND_COL_SIZE = False
        ss = Spreadsheet(workbook, worksheet_name, prj_info, currency)
        create_worksheet(ss, logger, parts)


def create_worksheet(ss, logger, parts):
    '''Create a worksheet using the info for the parts (including their HTML trees).'''
    # Force all currency related cells to use the "currency_format"
    ss.WRK_FORMATS['total_cost_currency']['num_format'] = ss.currency_format
    ss.WRK_FORMATS['unit_cost_currency']['num_format'] = ss.currency_format
    ss.WRK_FORMATS['currency']['num_format'] = ss.currency_format
    ss.WRK_FORMATS['currency_unit']['num_format'] = ss.currency_format_unit
    # Enable test wrap if we will adjust the sizes
    if ss.ADJUST_ROW_AND_COL_SIZE:
        ss.WRK_FORMATS['header']['text_wrap'] = True
        ss.WRK_FORMATS['part_format']['text_wrap'] = True
        ss.WRK_FORMATS['part_format_obsolete']['text_wrap'] = True
    # Create the various format styles used by various spreadsheet items.
    ss.wrk_formats = {}
    for k, v in ss.WRK_FORMATS.items():
        ss.wrk_formats[k] = ss.workbook.add_format(v)
    # Add the distinctive header format for each distributor to the `dict` of formats.
    base_hdr_format = ss.WRK_FORMATS['global']
    for d in ss.DISTRIBUTORS:
        hdr_format = base_hdr_format.copy()
        hdr_format.update(get_distributor_info(d).label.format)
        ss.wrk_formats[d] = ss.workbook.add_format(hdr_format)

    wks = ss.wks
    prj_info = ss.prj_info
    # Set the row & column for entering the part information in the sheet.
    START_COL = 0
    BOARD_QTY_ROW = ss.PRJ_INFO_START
    UNIT_COST_ROW = BOARD_QTY_ROW + 1
    TOTAL_COST_ROW = BOARD_QTY_ROW + 2
    START_ROW = ss.START_ROW
    LABEL_ROW = START_ROW + 1
    COL_HDR_ROW = LABEL_ROW + 1
    LAST_PART_ROW = COL_HDR_ROW + len(parts) - 1
    next_row = ss.PRJ_INFO_START

    # Load the global part information (not distributor-specific) into the sheet.
    # next_col = the column immediately to the right of the global data.
    # qty_col = the column where the quantity needed of each part is stored.
    next_line, next_col, refs_col, qty_col, columns_global = add_globals_to_worksheet(ss, logger, START_ROW, START_COL, TOTAL_COST_ROW, parts)
    ss.globals_width = next_col - 1
    # Create a defined range for the global data.
    ss.define_name_range('global_part_data', START_ROW, START_COL, LAST_PART_ROW, next_col - 1)

    for i_prj, p_info in enumerate(prj_info):
        # Add project information to track the project (in a printed version of the BOM) and the date because of price variations.
        i_prj_str = str(i_prj) if len(prj_info) > 1 else ''
        if ss.INCLUDE_PRJ_INFO:
            wks.write(next_row, START_COL, 'Prj{}:'.format(i_prj_str), ss.wrk_formats['proj_info_field'])
            wks.write(next_row, START_COL+1, p_info['title'], ss.wrk_formats['proj_info'])
            wks.write(next_row+1, START_COL, 'Co.:', ss.wrk_formats['proj_info_field'])
            wks.write(next_row+1, START_COL+1, p_info['company'], ss.wrk_formats['proj_info'])
            wks.write(next_row+2, START_COL, 'Prj date:', ss.wrk_formats['proj_info_field'])
            wks.write(next_row+2, START_COL+1, p_info['date'], ss.wrk_formats['proj_info'])

        # Create the cell where the quantity of boards to assemble is entered.
        # Place the board qty cells near the right side of the global info.
        ss.write_string(next_row, next_col - 2, 'Board Qty' + i_prj_str + ':', 'board_qty')
        # Set initial board quantity.
        wks.write(next_row, next_col - 1, p_info.get('qty', ss.DEFAULT_BUILD_QTY), ss.wrk_formats['board_qty'])
        # Define the named cell where the total board quantity can be found.
        qty_name = 'BoardQty' + i_prj_str
        ss.define_name_ref(qty_name, next_row, next_col - 1)

        # Create the cell to show total cost of board parts for each distributor.
        ss.write_string(next_row + 2, next_col - 2, 'Total Cost' + i_prj_str + ':', 'total_cost_label')
        wks.write_comment(next_row + 2, next_col - 2, 'Use the minimum extend price across distributors not taking account available quantities.')
        # Define the named cell where the total cost can be found.
        total_name = 'TotalCost' + i_prj_str
        ss.define_name_ref(total_name, next_row + 2, next_col - 1)

        # Create the cell to show unit cost of (each project) board parts.
        ss.write_string(next_row+1, next_col - 2, 'Unit Cost{}:'.format(i_prj_str), 'unit_cost_label')
        wks.write(next_row+1, next_col - 1, "={}/{}".format(total_name, qty_name), ss.wrk_formats['unit_cost_currency'])

        next_row += ss.PRJ_INFO_ROWS

    # Add general information of the scrap to track price modifications.
    if ss.ADD_DATE_TOP:
        ss.add_date(next_row, START_COL)
    # Add the total cost of all projects together.
    if len(prj_info) > 1:
        # Create the row to show total cost of board parts for each distributor.
        ss.write_string(next_row, next_col - 2, 'Total Prjs Cost:', 'total_cost_label')
        # Define the named cell where the total cost can be found.
        ss.define_name_ref('TotalCost', next_row, next_col - 1)
    next_row += 1

    # Freeze view of the global information and the column headers, but
    # allow the distributor-specific part info to scroll.
    wks.freeze_panes(COL_HDR_ROW, next_col)

    # Make a list of alphabetically-ordered distributors with web distributors before locals.
    logger.log(DEBUG_OVERVIEW, 'Sorting the distributors...')
    if ss.SORT_DISTRIBUTORS:
        web_dists = sorted([d for d in ss.DISTRIBUTORS if get_distributor_info(d).is_web()])
        local_dists = sorted([d for d in ss.DISTRIBUTORS if get_distributor_info(d).is_local()])
        dist_list = web_dists + local_dists
    else:
        dist_list = ss.DISTRIBUTORS

    # Load the part information from each distributor into the sheet.
    logger.log(DEBUG_OVERVIEW, 'Writing the distributor part information...')
    for dist in dist_list:
        dist_start_col = next_col
        next_col = add_dist_to_worksheet(ss, logger, columns_global,
                                         START_ROW, dist_start_col,
                                         UNIT_COST_ROW, TOTAL_COST_ROW,
                                         refs_col, qty_col, dist, parts)
        # Create a defined range for each set of distributor part data.
        ss.define_name_range('{}_part_data'.format(dist), START_ROW, dist_start_col, LAST_PART_ROW, next_col - 1)

    # Add general information of the scrap to track price modifications.
    if ss.ADD_DATE_BOTTOM:
        ss.add_date(next_line+1, START_COL)
        next_line += 1
    # Add the KiCost package information at the end of the spreadsheet to debug
    # information at the forum and "advertising".
    wks.write(next_line+1, START_COL, ss.ABOUT_MSG, ss.wrk_formats['about_msg'])
    # Optionally adjust cell sizes
    if ss.ADJUST_ROW_AND_COL_SIZE:
        ss.adjust_row_and_col_sizes(logger)


def add_globals_to_worksheet(ss, logger, start_row, start_col, total_cost_row, parts):
    '''Add global part data to the spreadsheet.'''

    logger.log(DEBUG_OVERVIEW, 'Writing the global part information...')

    wks = ss.wks
    # Columns for the various types of global part data.
    columns = ss.GLOBAL_COLUMNS.copy()
    # Created a list of columns sorted by column position
    columns_list = [None] * len(columns)
    for id, data in columns.items():
        # Remove not used columns by the field not founded in ALL the parts. This give
        # better visualization on notebooks (small screens) and optimization to print.
        if id in ['manf', 'desc'] and not next(iter(filter(lambda part: part.fields.get(id), parts)), None):
            continue
        columns_list[data['col']] = id
    # Compact the list
    columns_list = [c for c in columns_list if c]

    # Add quantity columns to deal with different quantities in the BOM files. The
    # original quantity column will be the total of each item. For check the number
    # of BOM files read, see the length of p[?]['manf#_qty'], if it is a `list()`
    # instance, if don't, the length is always `1`.
    num_prj = max([len(part.fields.get('manf#_qty', [])) if isinstance(part.fields.get('manf#_qty', []), list) else 1 for part in parts])
    if num_prj > 1:
        insert_idx = columns_list.index('qty')
        for i_prj in range(num_prj):
            # Add one column to quantify the quantity for each project.
            s_prj = str(i_prj)
            name = 'qty_prj' + s_prj
            columns[name] = columns['qty'].copy()
            columns[name]['label'] = 'Qty.Prj' + s_prj
            columns[name]['comment'] = 'Total number of each part needed to assembly the project {}.'.format(s_prj)
            columns_list.insert(insert_idx, name)
            insert_idx += 1

    # Enter user-defined fields into the global part data columns structure.
    insert_idx = columns_list.index('footprint')
    for user_field in list(reversed(ss.USER_FIELDS)):
        # Separate the information
        comment = 'User-defined field.'
        level = 0
        if isinstance(user_field, dict):
            # Support a dict with extra info:
            field = user_field['field']
            user_field_id = field.lower()
            comment = user_field.get('comment', comment)
            level = user_field.get('level', level)
            label = user_field.get('label', field)
        else:
            # Just the name of the field
            user_field_id = user_field.lower()
            label = user_field
        # Skip the user field if it's already in the list of data columns.
        if user_field_id not in columns:
            # Insert user field immediately to right of the 'desc' column.
            columns_list.insert(insert_idx, user_field_id)
            columns[user_field_id] = {'level': level, 'label': label, 'width': None, 'comment': comment, 'static': True}

    num_cols = len(columns_list)

    row = start_row  # Start building global section at this row.

    # Add label for global section.
    wks.merge_range(row, start_col, row, start_col + num_cols - 1, "Global Part Info", ss.wrk_formats['global'])
    row += 1  # Go to next row.

    # Add column headers.
    # Memorize the columns positions, this `col`
    logger.debug(columns_list)
    col = {}
    for c, k in enumerate(columns_list):
        ss.write_string(row, c, columns[k]['label'], 'header')
        wks.write_comment(row, c, columns[k]['comment'])
        ss.set_column(c, columns[k]['width'], columns[k]['level'])
        col[k] = c
    row += 1  # Go to next row.

    num_parts = len(parts)
    PART_INFO_FIRST_ROW = row  # Starting row of part info.
    PART_INFO_LAST_ROW = PART_INFO_FIRST_ROW + num_parts - 1  # Last row of part info.

    # Add data for each part to the spreadsheet.
    # Order the references and collapse, if asked:
    # e.g. J3, J2, J1, J6 => J1, J2, J3 J6. # `collapse=False`
    # e.g. J3, J2, J1, J6 => J1-J3, J6.. # `collapse=True`
    for part in parts:
        part.collapsed_refs, part.first_ref = order_refs(part.refs, collapse=ss.COLLAPSE_REFS, ref_sep=ss.PART_NSEQ_SEPRTR)

    # Then, order the part references with priority ref prefix, ref num, and subpart num.
    def get_ref_key(part):
        match = PART_REF_REGEX.match(part.first_ref)
        if not match:
            return [part.collapsed_refs, 0, 0]
        subpart_num = match.group('subpart_num')
        return [match.group('prefix'), int(match.group('ref_num')), int(subpart_num) if subpart_num else 0]
    parts.sort(key=get_ref_key)

    # Add the global part data to the spreadsheet.
    used_currencies = set()
    for part in parts:

        # Enter part references.
        ss.write_string(row, start_col + col['refs'], part.collapsed_refs, 'part_format')

        # Enter more static data for the part.
        for field in columns_list:
            if columns[field]['static'] is False:
                continue
            # Fields found in the XML are lower-cased, so do the same for the column key.
            field_name = field.lower().strip()
            field_value = part.fields.get(field_name)
            cell_format = 'part_format'
            n_col = start_col + col[field]
            if field_name == 'manf#':
                # Note: empty manf# with link will show the URL
                link = part.fields.get('datasheet')
                if not link:
                    # Use the the datasheet link got in the distributor if not available any in the BOM / schematic.
                    link = part.datasheet
                # Mark obsolete parts
                if part.lifecycle and part.lifecycle == 'obsolete':
                    cell_format = 'part_format_obsolete'
                if link and validate_url(link):
                    # Just put the link if is a valid format.
                    ss.write_url(row, n_col, link, string=field_value, cell_format=cell_format)
                    continue
            if field_value is None:
                # Skip empty cells
                continue
            if field_name == 'footprint':
                # TODO add future dependence of "electro-grammar" (https://github.com/kitspace/electro-grammar)
                field_value_footprint = re.findall(r'\:(.*)', field_value)
                if field_value_footprint:
                    field_value = field_value_footprint[0]
            ss.write_string(row, n_col, field_value, cell_format)

        # Enter total part quantity needed.
        qty, qty_n = partgroup_qty(part)
        if isinstance(qty, list):
            # Multifiles BOM case, write each quantity and after,
            # in the 'qty' column the total quantity as ceil of
            # the total quantity (to ceil use a Microsoft Excel
            # compatible function.
            total = 0
            for i_prj, p_info in enumerate(ss.prj_info):
                value = qty_n[i_prj] * p_info.get('qty', ss.DEFAULT_BUILD_QTY)
                total += value
                id = str(i_prj)
                # Qty.PrjN
                wks.write_formula(row, start_col + col['qty_prj'+id], qty[i_prj].format('BoardQty'+id), ss.wrk_formats['part_format'], value=value)
            # Build Quantity
            wks.write_formula(row, start_col + col['qty'],
                              '=CEILING(SUM({}:{}),1)'.format(xl_rowcol_to_cell(row, start_col + col['qty_prj0']),
                                                              xl_rowcol_to_cell(row, start_col + col['qty']-1)),
                              ss.wrk_formats['part_format'],
                              value=ceil(total))
        else:
            # Build Quantity
            wks.write_formula(row, start_col + col['qty'],
                              qty.format('BoardQty'), ss.wrk_formats['part_format'],
                              value=ceil(qty_n * ss.prj_info[0].get('qty', ss.DEFAULT_BUILD_QTY)))

        # Gather the cell references for calculating minimum unit price and part availability.
        dist_unit_prices = []
        dist_qty_avail = []
        dist_qty_purchased = []
        dist_code_avail = []
        dist_ext_prices = []
        for dist in sorted(ss.DISTRIBUTORS):

            # Get the currencies used among all distributors.
            used_currencies.add(part.currency.get(dist, DEFAULT_CURRENCY))

            # Get the name of the data range for this distributor.
            dist_data_rng = '{}_part_data'.format(dist)

            # Get the contents of the unit price cell for this part (row) and distributor (column+offset).
            dist_unit_prices.append('INDIRECT(ADDRESS(ROW(),COLUMN({})+2))'.format(dist_data_rng))

            # Get the contents of the quantity purchased cell for this part and distributor
            # unless the unit price is not a number in which case return 0.
            dist_qty_purchased.append('IF(ISNUMBER(INDIRECT(ADDRESS(ROW(),COLUMN({0})+2))),INDIRECT(ADDRESS(ROW(),COLUMN({0})+1)),0)'.format(dist_data_rng))

            # Get the contents of the quantity available cell of this part from this distributor.
            dist_qty_avail.append('INDIRECT(ADDRESS(ROW(),COLUMN({})+0))'.format(dist_data_rng))

            # Get the contents of the manufacture and distributors codes.
            dist_code_avail.append('ISBLANK(INDIRECT(ADDRESS(ROW(),COLUMN({})+4)))'.format(dist_data_rng))

            # Get the contents of the manufacture and distributors codes.
            dist_ext_prices.append('INDIRECT(ADDRESS(ROW(),COLUMN({})+3))'.format(dist_data_rng))

        # If part do not have manf# code or distributor codes, color quantity cell gray.
        wks.conditional_format(
            row, start_col + col['qty'],
            row, start_col + col['qty'],
            {
                'type': 'formula',
                'criteria': '=AND(ISBLANK({g}),{d})'.format(
                    g=xl_rowcol_to_cell(row, start_col + col['manf#']),  # Manf# column also have to be blank.
                    d=(','.join(dist_code_avail) if dist_code_avail else 'TRUE()')
                 ),
                'format': ss.wrk_formats['not_manf_codes']
            }
        )

        # Enter the spreadsheet formula for calculating the minimum extended price (based on the unit price found on next formula).
        wks.write_formula(
            row, start_col + col['ext_price'],
            '=iferror({qty}*{unit_price},"")'.format(
                qty=xl_rowcol_to_cell(row, start_col + col['qty']),
                unit_price=xl_rowcol_to_cell(row, start_col + col['unit_price'])
            ),
            ss.wrk_formats['currency']
        )

        # If not asked to scrape, to correlate the prices and available quantities.
        if ss.DISTRIBUTORS:
            # Enter the spreadsheet formula to find this part's minimum unit price across all distributors.
            wks.write_formula(row, start_col + col['unit_price'], '=MINA({})'.format(','.join(dist_unit_prices)), ss.wrk_formats['currency_unit'])

            # If part is unavailable from all distributors, color quantity cell red.
            wks.conditional_format(
                row, start_col + col['qty'],
                row, start_col + col['qty'],
                {
                    'type': 'formula',
                    'criteria': '=IF(SUM({})=0,1,0)'.format(','.join(dist_qty_avail)),
                    'format': ss.wrk_formats['not_available']
                }
            )

            # If total available part quantity is less than needed quantity, color cell orange.
            wks.conditional_format(
                row, start_col + col['qty'],
                row, start_col + col['qty'],
                {
                    'type': 'cell',
                    'criteria': '>',
                    'value': '=SUM({})'.format(','.join(dist_qty_avail)),
                    'format': ss.wrk_formats['too_few_available']
                }
            )

            # If total purchased part quantity is less than needed quantity, color cell yellow.
            wks.conditional_format(
                row, start_col + col['qty'],
                row, start_col + col['qty'],
                {
                    'type': 'cell',
                    'criteria': '>',
                    'value': '=SUM({})'.format(','.join(dist_qty_purchased)),
                    'format': ss.wrk_formats['too_few_purchased'],
                }
            )

        # Enter part shortage quantity.
        try:
            wks.write(row, start_col + col['short'], 0)  # slack quantity. (Not handled, yet.)
        except KeyError:
            pass

        row += 1  # Go to next row.

    # Sum the extended prices for all the parts to get the total minimum cost.
    # If have read multiple BOM file calculate it by `SUMPRODUCT()` of the
    # board project quantity components 'qty_prj*' by unitary price 'Unit$'.
    total_cost_col = start_col + col['ext_price']
    if isinstance(qty, list):
        unit_price_col = start_col + col['unit_price']
        unit_price_range = xl_range(PART_INFO_FIRST_ROW, unit_price_col, PART_INFO_LAST_ROW, unit_price_col)
        # Add each project board total.
        for i_prj in range(len(qty)):
            qty_col = start_col + col['qty_prj{}'.format(i_prj)]
            wks.write(total_cost_row + ss.PRJ_INFO_ROWS*i_prj, total_cost_col,
                      '=SUMPRODUCT({qty_range},{unit_price_range})'.format(
                            unit_price_range=unit_price_range,
                            qty_range=xl_range(PART_INFO_FIRST_ROW, qty_col,
                                               PART_INFO_LAST_ROW, qty_col)),
                      ss.wrk_formats['total_cost_currency'])
        # Add total of the spreadsheet, this can be equal or bigger than
        # than the sum of the above totals, because, in the case of partial
        # or fractional quantity of one part or subpart, the total quantity
        # column 'qty' will be the ceil of the sum of the other ones.
        total_cost_row = start_row - 1  # Change the position of the total price cell.
    wks.write(total_cost_row, total_cost_col, '=SUM({sum_range})'.format(
              sum_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                                 PART_INFO_LAST_ROW, total_cost_col)),
              ss.wrk_formats['total_cost_currency'])

    # Add the total purchase and others purchase informations.
    if ss.DISTRIBUTORS:
        next_line = row + 1
        ss.write_string(next_line, start_col + col['unit_price'], 'Total Purchase:', 'total_cost_label')
        wks.write_comment(next_line, start_col + col['unit_price'], 'This is the total of your cart across all distributors.')
        wks.write(next_line, start_col + col['ext_price'], '=SUM({})'.format(','.join(dist_ext_prices)), ss.wrk_formats['total_cost_currency'])
        # Purchase general description, it may be used to distinguish carts of different projects.
        next_line = next_line + 1
        ss.write_string(next_line, start_col + col['unit_price'], 'Purchase description:', 'description')
        wks.write_comment(next_line, start_col + col['unit_price'],
                          'This description will be added to all purchased parts label and may be used to distinguish the ' +
                          'component of different projects.')
        ss.define_name_ref('PURCHASE_DESCRIPTION', next_line, col['ext_price'])

    # Get the actual currency rate to use.
    next_line = row + 1
    used_currencies = sorted(list(used_currencies))
    logger.log(DEBUG_OVERVIEW, 'Getting distributor currency convertion rate {} to {}...'.format(used_currencies, ss.currency_alpha3))
    if len(used_currencies) > 1:
        if ss.currency_alpha3 in used_currencies:
            used_currencies.remove(ss.currency_alpha3)
        wks.write(next_line, start_col + col['value'],
                  'Used currency rates:', ss.wrk_formats['description'])
        next_line = next_line + 1
    for used_currency in used_currencies:
        if used_currency != ss.currency_alpha3:
            wks.write(next_line, start_col + col['value'],
                      '{c}({c_s})/{d}({d_s}):'.format(c=ss.currency_alpha3, d=used_currency, c_s=ss.currency_symbol,
                                                      d_s=get_currency_symbol(used_currency, locale=DEFAULT_LANGUAGE)
                                                      ),
                      ss.wrk_formats['description']
                      )
            ss.define_name_ref('{c}_{d}'.format(c=ss.currency_alpha3, d=used_currency), next_line, col['value'] + 1)
            try:
                wks.write(next_line, col['value'] + 1, currency_convert(1, used_currency, ss.currency_alpha3))
            except ValueError as e:
                raise KiCostError(str(e) + ' in ' + part.collapsed_refs, ERR_FIELDS)
            next_line = next_line + 1

    # Return column following the globals so we know where to start next set of cells.
    # Also return the columns where the references and quantity needed of each part is stored.
    return next_line, start_col + num_cols, start_col + col['refs'], start_col + col['qty'], col


def add_dist_to_worksheet(ss, logger, columns_global, start_row, start_col,
                          unit_cost_row, total_cost_row, part_ref_col, part_qty_col,
                          dist, parts):
    '''Add distributor-specific part data to the spreadsheet.'''

    info = get_distributor_info(dist)
    order = info.order
    label = info.label.name
    logger.log(DEBUG_OVERVIEW, '# Writing {}'.format(label))

    wks = ss.wks
    # Columns for the various types of distributor-specific part data.
    columns = deepcopy(ss.DISTRIBUTOR_COLUMNS)
    if not ss.SUPPRESS_CAT_URL:
        # Add a extra column to the hyperlink.
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
    wks.merge_range(row, start_col, row, start_col + num_cols - 1, label, ss.wrk_formats[dist])
    # if info.is_web():
    #     ss.write_url(row, start_col, info.label.url, ss.wrk_formats[dist], label)
    row += 1  # Go to next row.

    # Add column headers, comments, and outline level (for hierarchy).
    for k in list(columns.keys()):
        col = start_col + columns[k]['col']  # Column index for this column.
        ss.write_string(row, col, columns[k]['label'], 'header')
        wks.write_comment(row, col, columns[k]['comment'])
        ss.set_column(col, columns[k]['width'], columns[k]['level'])
    row += 1  # Go to next row.

    num_parts = len(parts)
    # For check the number of BOM files read, see the length of p[?]['manf#_qty'],
    # if it is a `list()` instance, if don't, the length is always `1`.
    num_prj = max([len(part.fields.get('manf#_qty', [])) if isinstance(part.fields.get('manf#_qty', []), list) else 1 for part in parts])

    # Add distributor data for each part.
    PART_INFO_FIRST_ROW = row  # Starting row of part info.
    PART_INFO_LAST_ROW = PART_INFO_FIRST_ROW + num_parts - 1  # Last row of part info.

    for part in parts:

        dist_part_num = part.part_num.get(dist)  # Get the distributor part number.
        price_tiers = part.price_tiers.get(dist, {})  # Extract price tiers from distributor HTML page tree.
        dist_qty_avail = part.qty_avail.get(dist)
        # If the part number doesn't exist, just leave this row blank.
        # if dist_part_num is None or dist_qty_avail is None or len(price_tiers) == 0:
        if dist_part_num is None:
            row += 1  # Skip this row and go to the next.
            continue
        dist_info_dist = part.info_dist.get(dist, {})
        dist_currency = part.currency.get(dist)  # Extract currency used by the distributor.

        # Enter distributor part number for ordering purposes.
        if dist_part_num:
            wks.write(row, start_col + columns['part_num']['col'], dist_part_num, ss.wrk_formats['part_format'])
        else:
            if ss.SUPPRESS_CAT_URL:
                dist_part_num = 'Link'  # To use as text for the link.
        try:
            # Add a comment in the 'cat#' column with extra information gotten in the distributor web page.
            comment = '\n'.join(sorted([k.capitalize()+SEPRTR+' '+v for k, v in dist_info_dist.items() if k in ss.extra_info_display]))
            if comment:
                wks.write_comment(row, start_col + columns['part_num']['col'], comment)
        except Exception:
            pass

        # Enter a link to the distributor webpage for this part, even if there
        # is no valid quantity or pricing for the part (see next conditional).
        # Having the link present will help debug if the extraction of the
        # quantity or pricing information was done correctly.
        dist_url = part.url.get(dist)
        if dist_url:
            if ss.SUPPRESS_CAT_URL:
                ss.write_url(row, start_col + columns['part_num']['col'], dist_url, string=dist_part_num)
            else:
                ss.write_url(row, start_col + columns['link']['col'], dist_url)

        # Enter quantity of part available at this distributor unless it is None
        # which means the part is not stocked.
        if dist_qty_avail:
            wks.write(row, start_col + columns['avail']['col'], dist_qty_avail, ss.wrk_formats['part_format'])
        else:
            wks.write(row, start_col + columns['avail']['col'], 'NonStk', ss.wrk_formats['not_stocked'])
            wks.write_comment(row, start_col + columns['avail']['col'], 'This part is listed but is not normally stocked.')

        # Purchase quantity always starts as blank because nothing has been purchased yet.
        wks.write(row, start_col + columns['purch']['col'], '', None)

        # Add pricing information if it exists.
        if len(list(price_tiers)) > 0:
            # Add the price for a single unit if it doesn't already exist in the tiers.
            try:
                min_qty = min(price_tiers.keys())
                minimum_order_qty = min_qty  # Update the minimum order quantity.
                if min_qty > 1:
                    price_tiers[1] = price_tiers[min_qty]  # Set unit price to price of lowest available quantity.
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
            if dist_currency == ss.currency_alpha3:
                wks.write_formula(
                    row, unit_price_col,
                    '=iferror(lookup(if({purch_qty}="",{needed_qty},{purch_qty}),{{{qtys}}},{{{prices}}}),"")'.format(
                        needed_qty=xl_rowcol_to_cell(row, part_qty_col),
                        purch_qty=xl_rowcol_to_cell(row, purch_qty_col),
                        qtys=','.join([str(q) for q in qtys]),
                        prices=','.join([str(price_tiers[q]) for q in qtys])), ss.wrk_formats['currency_unit'])
            else:
                wks.write_formula(
                    row, unit_price_col,
                    '=iferror({rate}*lookup(if({purch_qty}="",{needed_qty},{purch_qty}),{{{qtys}}},{{{prices}}}),"")'.format(
                        rate='{c}_{d}'.format(c=ss.currency_alpha3, d=dist_currency),  # Currency rate used to this distributor.
                        needed_qty=xl_rowcol_to_cell(row, part_qty_col),
                        purch_qty=xl_rowcol_to_cell(row, purch_qty_col),
                        qtys=','.join([str(q) for q in qtys]),
                        prices=','.join([str(price_tiers[q]) for q in qtys])), ss.wrk_formats['currency_unit'])

            # Add a comment to the cell showing the qty/price breaks.
            dist_currency_symbol = get_currency_symbol(dist_currency, locale=DEFAULT_LANGUAGE)
            price_break_info = 'Qty/Price Breaks ({c}):\n  Qty  -  Unit{s}  -  Ext{s}\n================'.format(c=dist_currency, s=dist_currency_symbol)
            for q in qtys[1 if minimum_order_qty == 1 else 2:]:
                # Skip the unity quantity for the tip balloon if it not allow to purchase in the distributor.
                price = price_tiers[q]
                price_fmt = format_currency(price, dist_currency, locale=DEFAULT_LANGUAGE)
                priceq_fmt = format_currency(price*q, dist_currency, locale=DEFAULT_LANGUAGE)
                price_break_info += '\n{:>6d} {:>7s} {:>10s}'.format(q, price_fmt, priceq_fmt)
            wks.write_comment(row, unit_price_col, price_break_info)

            # Conditional format to show no quantity is available.
            wks.conditional_format(
                row, start_col + columns['avail']['col'],
                row, start_col + columns['avail']['col'],
                {
                    'type': 'cell',
                    'criteria': '==',
                    'value': 0,
                    'format': ss.wrk_formats['not_available']
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
                    'format': ss.wrk_formats['too_few_available']
                }
            )

            # Conditional format to show that the part have a minimum order quantity not respected.
            if minimum_order_qty > 1:
                wks.conditional_format(
                    row, start_col + columns['purch']['col'],
                    row, start_col + columns['purch']['col'],
                    {
                        'type': 'formula',
                        'criteria': '=AND({q}>0,{q}<{moq})'.format(
                            q=xl_rowcol_to_cell(row, start_col + columns['purch']['col']),
                            moq=minimum_order_qty
                        ),
                        'format': ss.wrk_formats['order_min_qty']
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
                    'format': ss.wrk_formats['order_too_much']
                }
            )

            # Enter the formula for the extended price = purch qty * unit price.
            wks.write_formula(
                row, ext_price_col,
                '=iferror(if({purch_qty}="",{needed_qty},{purch_qty})*{unit_price},"")'.format(
                    needed_qty=xl_rowcol_to_cell(row, part_qty_col),
                    purch_qty=xl_rowcol_to_cell(row, purch_qty_col),
                    unit_price=xl_rowcol_to_cell(row, unit_price_col)),
                ss.wrk_formats['currency'])

            if len(ss.DISTRIBUTORS) > 1:  # Just use the best price highlight if more than one distributor.
                # Conditionally format the extended price cell that contains the best price.
                wks.conditional_format(row, ext_price_col, row, ext_price_col, {
                    'type': 'cell',
                    'criteria': '<=',
                    'value': xl_rowcol_to_cell(row, part_qty_col+2),
                    # This is the global data cell holding the minimum extended price for this part.
                    'format': ss.wrk_formats['best_price']
                })
                # Conditionally format the unit price cell that contains the best price.
                wks.conditional_format(row, unit_price_col, row, unit_price_col, {
                    'type': 'cell',
                    'criteria': '<=',
                    'value': xl_rowcol_to_cell(row, part_qty_col+1),
                    # This is the global data cell holding the minimum unit price for this part.
                    'format': ss.wrk_formats['best_price']
                })

        # Finished processing distributor data for this part.
        row += 1  # Go to next row.

    total_cost_col = start_col + columns['ext_price']['col']
    unit_cost_col = start_col + columns['unit_price']['col']
    dist_cat_col = start_col + columns['part_num']['col']

    # If more than one file (multi-files mode) show how many
    # parts of each BOM as found at this distributor and
    # the correspondent total price.
    if num_prj > 1:
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
                      ss.wrk_formats['total_cost_currency'])
            # Show how many parts were found at this distributor.
            wks.write(row, dist_cat_col,
                      '=COUNTIFS({price_range},"<>",{qty_range},"<>0",{qty_range},"<>")&" of "&COUNTIFS({qty_range},"<>0",'
                      '{qty_range},"<>")&" parts found"'.format(price_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                                                                PART_INFO_LAST_ROW, total_cost_col),
                                                                qty_range=xl_range(PART_INFO_FIRST_ROW, qty_prj_col,
                                                                                   PART_INFO_LAST_ROW, qty_prj_col)),
                      ss.wrk_formats['found_part_pct'])
            wks.write_comment(row, dist_cat_col, 'Number of parts found at this distributor for the project {}.'.format(i_prj))
        total_cost_row = PART_INFO_FIRST_ROW - 3  # Shift the total price in this distributor.

    # Sum the extended prices for all the parts to get the total cost from this distributor.
    wks.write(total_cost_row, total_cost_col, '=SUM({sum_range})'.format(
        sum_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                           PART_INFO_LAST_ROW, total_cost_col)),
              ss.wrk_formats['total_cost_currency'])
    # Show how many parts were found at this distributor.
    wks.write(total_cost_row, dist_cat_col,
              # '=COUNTIF({count_range},"<>")&" of "&ROWS({count_range})&" parts found"'.format(
              '=(COUNTA({count_range})&" of "&ROWS({count_range})&"'
              ' parts found")'.format(count_range=xl_range(PART_INFO_FIRST_ROW, total_cost_col,
                                      PART_INFO_LAST_ROW, total_cost_col)),
              ss.wrk_formats['found_part_pct'])
    wks.write_comment(total_cost_row, dist_cat_col, 'Number of parts found at this distributor.')

    # Add list of part numbers and purchase quantities for ordering from this distributor.
    ORDER_START_COL = start_col + 1
    ORDER_FIRST_ROW = PART_INFO_LAST_ROW + 3
    ORDER_LAST_ROW = ORDER_FIRST_ROW + num_parts - 1

    # Write the header and how many parts are being purchased.
    purch_qty_col = start_col + columns['purch']['col']
    ext_price_col = start_col + columns['ext_price']['col']
    ORDER_HEADER = PART_INFO_LAST_ROW + 2
    wks.write_formula(  # Expended many in this distributor.
        ORDER_HEADER, ext_price_col,
        '=SUMIF({count_range},">0",{price_range})'.format(
            count_range=xl_range(PART_INFO_FIRST_ROW, purch_qty_col, PART_INFO_LAST_ROW, purch_qty_col),
            price_range=xl_range(PART_INFO_FIRST_ROW, ext_price_col, PART_INFO_LAST_ROW, ext_price_col),
        ),
        ss.wrk_formats['total_cost_currency']
    )
    wks.write_formula(  # Quantity of purchased part in this distributor.
        ORDER_HEADER, purch_qty_col,
        '=IFERROR(IF(OR({count_range}),COUNTIFS({count_range},">0",{count_range_price},"<>")&" of "&'
        '(ROWS({count_range_price})-COUNTBLANK({count_range_price}))&" parts purchased",""),"")'.format(
            count_range=xl_range(PART_INFO_FIRST_ROW, purch_qty_col, PART_INFO_LAST_ROW, purch_qty_col),
            count_range_price=xl_range(PART_INFO_FIRST_ROW, ext_price_col, PART_INFO_LAST_ROW, ext_price_col)
        ),
        ss.wrk_formats['found_part_pct']
    )
    wks.write_comment(ORDER_HEADER, purch_qty_col, 'Copy the information below to the BOM import page of the distributor web site.')
    if order.url:
        ss.write_url(ORDER_HEADER, purch_qty_col-1, order.url, string='Buy here')

    # Write the spreadsheet code to multiple lines to create the purchase codes to
    # be used in this current distributor.
    cols = order.cols
    if not cols:
        logger.log(DEBUG_OVERVIEW, "Purchase list codes for {d} will not be generated: no information provided.".format(d=label))
        return start_col + num_cols  # If not created the distributor definition, jump this final code part.

    if ORDER_COL_USERFIELDS in cols:
        # It is requested all the user fields at the purchase code,
        # replace the virtual annotation provided by `ORDER_COL_USERFIELDS`
        # by all user fields in the spreadsheet. This keep the compatibility
        # and configuration possibility for other features.
        idx = cols.index(ORDER_COL_USERFIELDS)  # Find the first occurrence.
        del cols[idx]
        cols_user = list(columns_global.keys())
        for r in set(cols+['refs', 'qty', 'value', 'footprint', 'unit_price', 'ext_price', 'manf#', 'part_num', 'purch', 'desc']):
            try:
                cols_user.remove(r)
            except ValueError:
                pass
        logger.log(DEBUG_OVERVIEW, "Add the {f} information for the {d} purchase list code.".format(d=label, f=cols_user))
        cols[idx:idx] = cols_user

    # Create the header of the purchase codes, if present the definition.
    if order.header:
        wks.write_formula(ORDER_FIRST_ROW, ORDER_START_COL,
                          '=IFERROR(IF(COUNTIFS({count_range},">0",{count_range_price},"<>")>0,"{header}",""),"")'
                          .format(count_range=xl_range(PART_INFO_FIRST_ROW, purch_qty_col,
                                                       PART_INFO_LAST_ROW, purch_qty_col),
                                  count_range_price=xl_range(PART_INFO_FIRST_ROW, ext_price_col,
                                                             PART_INFO_LAST_ROW, ext_price_col),
                                  header=order.header),
                          ss.wrk_formats['found_part_pct'])
        if order.info:
            wks.write_comment(ORDER_FIRST_ROW, ORDER_START_COL, order.info)
        ORDER_FIRST_ROW = ORDER_FIRST_ROW + 1  # Push all the code list one row.
        ORDER_LAST_ROW = ORDER_LAST_ROW + 1

    if not('purch' in cols and ('part_num' in cols or 'manf#' in cols)):
        logger.log(DEBUG_OVERVIEW, "Purchase list codes for {d} will not be generated: no stock# of manf# format defined.".format(d=label))
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
        order_info_func_model = re.sub(r'[\s\n]', '', order_info_func_model)  # Strip all the whitespace from the function string.

        # Create the line order by the fields specified by each distributor.
        delimier = ',"' + order.delimiter + '",'  # Function delimiter plus distributor code delimiter.
        order_part_info = []
        for col in cols:
            # Deal with conversion and string replace necessary to the correct distributors
            # code understanding.
            if col is None or (col not in columns and col not in columns_global):
                # Create an empty column escaping all the information, same when is asked
                # for a not present filed at the global column (`columns_global`) part or
                # distributors columns part (`columns`).
                order_part_info.append('')
                continue  # Doesn't need to calculate range or references, go check the next field.
            if col == 'purch':
                # Add text conversion if is a numeric cell.
                order_part_info.append('TEXT({},"##0")'.format(order_info_func_model))
            elif col not in ['part_num', 'purch', 'manf#']:
                # All comment and description columns (that are not quantity and catalogue code)
                # should respect the allowed characters. These are text informative columns.
                # if col=='refs':
                #     # If 'refs' column an additional rule to remove the subpart counter.
                #     order_info_func_parcial = 'REGEX({f},"\{c}\d+","","g")'.format(f=order_info_func_model,c=SUB_SEPRTR)
                #     This is not supported by Microsoft Excel. ## TODO
                # else:
                order_info_func_parcial = order_info_func_model
                if order.not_allowed_char and order.replace_by_char:
                    multi_replace = len(order.replace_by_char) > 1
                    for c, not_allowed_char in enumerate(order.not_allowed_char):
                        replace_by_char = order.replace_by_char[c if multi_replace else 0]
                        order_info_func_parcial = 'SUBSTITUTE({t},"{o}","{n}")'.format(t=order_info_func_parcial, o=not_allowed_char, n=replace_by_char)
                if order.limit:
                    order_info_func_parcial = 'LEFT({},{})'.format(order_info_func_parcial, order.limit)
                order_part_info.append(order_info_func_parcial)
            else:
                order_part_info.append(order_info_func_model)
            # Look for the `col` name into the distributor spreadsheet part
            # with don't find, it belongs to the global part.
            if col in columns:
                info_range = start_col + columns[col]['col']
            elif col in columns_global:
                info_range = columns_global[col]
            else:
                info_range = ""
                logger.warning(W_NOPURCH+"Not valid field `{f}` for purchase list at {d}.".format(f=col, d=label))
            info_range = xl_range(PART_INFO_FIRST_ROW, info_range,
                                  PART_INFO_LAST_ROW, info_range)
            # If the correspondent information is some description, it is allow to add the general
            # purchase designator. it is placed inside the "not allow characters" restriction.
            if col not in ['part_num', 'purch', 'manf#']:
                info_range = 'IF(PURCHASE_DESCRIPTION<>"",PURCHASE_DESCRIPTION&"{}","")'.format(ss.purchase_description_seprtr) + '&' + info_range
            # Create the part of formula that refers with one specific information.
            order_part_info[-1] = order_part_info[-1].format(
                        get_range=info_range,
                        qty='{qty}',  # keep all other for future replacement.
                        code='{code}',
                        order_first_row='{order_first_row}')
        # If already have some information, add the delimiter for
        # Microsoft Excel/LibreOffice Calc function.
        order_func = order_func.format(delimier.join(order_part_info))

        # These are the columns where the part catalog numbers and purchase quantities can be found.
        if 'part_num' in cols:
            purchase_code = start_col + columns['part_num']['col']
        elif 'manf#' in cols:
            purchase_code = start_col + columns_global['manf#']
        else:
            purchase_code = ""
            logger.warning(W_NOQTY+"Not valid quantity/code field `{f}` for purchase list at {d}.".format(f=col, d=label))
        purchase_code = xl_range(PART_INFO_FIRST_ROW, purchase_code, PART_INFO_LAST_ROW, purchase_code)
        purchase_qty = start_col + columns['purch']['col']
        purchase_qty = xl_range(PART_INFO_FIRST_ROW, purchase_qty, PART_INFO_LAST_ROW, purchase_qty)
        # Fill the formula with the control parameters.
        order_func = order_func.format(order_first_row=xl_rowcol_to_cell(ORDER_FIRST_ROW, 0, row_abs=True), code=purchase_code, qty=purchase_qty)
        # Now write the order_func into every row of the order in the given column.
        # dist_col = start_col + columns['unit_price']['col']
        # info_col = dist_col
        for r in range(ORDER_FIRST_ROW, ORDER_LAST_ROW + 1):
            wks.write_array_formula(xl_range(r, ORDER_START_COL, r, ORDER_START_COL), '{{={f}}}'.format(f=order_func))

    return start_col + num_cols  # Return column following the globals so we know where to start next set of cells.
