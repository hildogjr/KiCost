# -*- coding: utf-8 -*-
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

# Instructions to add new distributor:
# 1) Create a 'distributor.py' file in the same folder os this file;
# 2) Follow the same names and resource of the already implemented ones;
# 4) Declarate these functions above;
# 5) Create the standard color name that will be used in the title row of the spreadsheet;
# 6) The file and the dictionary label have to have the same string.

# Libriries of each distributor site.
from .local_lbl import get_local_price_tiers, get_local_part_num, get_local_qty_avail, get_local_part_html_tree
from .digikey import get_digikey_price_tiers, get_digikey_part_num, get_digikey_qty_avail, get_digikey_part_html_tree
from .newark import get_newark_price_tiers, get_newark_part_num, get_newark_qty_avail, get_newark_part_html_tree
from .mouser import get_mouser_price_tiers, get_mouser_part_num, get_mouser_qty_avail, get_mouser_part_html_tree
from .rs import get_rs_price_tiers, get_rs_part_num, get_rs_qty_avail, get_rs_part_html_tree
from .farnell import get_farnell_price_tiers, get_farnell_part_num, get_farnell_qty_avail, get_farnell_part_html_tree

# File's author information (do not change).
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# Distributors colors definitions, used to the spreadsheet title row.
# Tip: use the distributor color logo and avoid colors combination already used.
distributor_colors = {
    'local_lbl': [{ # Local price library.
            'font_color': 'black',
            'bg_color': '#909090'  # Darker grey.
        },
        {
            'font_color': 'black',
            'bg_color': '#c0c0c0'  # Lighter grey.
        },
    ],
    'digikey':{
        'font_color': 'white',
        'bg_color': '#CC0000'  # Digi-Key red.
    },
    'mouser': {
        'font_color': 'white',
        'bg_color': '#004A85'  # Mouser blue.
    },
    'newark': {
        'font_color': 'white',
        'bg_color': '#A2AE06'  # Newark/E14 olive green.
    },
    'rs': {
        'font_color': 'white',
        'bg_color': '#FF0000'  # RS Components red.
    },
    'farnell': {
        'font_color': 'white',
        'bg_color': '#FF6600'  # Farnell/E14 orange.
    },
}
