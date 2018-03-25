# -*- coding: utf-8 -*-

__author__='Giacinto Luigi Cerone'

from .farnell import *

# Place information about this distributor into the distributor dictionary.
from .. import distributor_dict
distributor_dict.update(
    {
        'farnell': {
            'module': 'farnell', # The directory name containing this file.
            'scrape': 'web',     # Allowable values: 'web' or 'local'.
            'label': 'Farnell',  # Distributor label used in spreadsheet columns.
            'order_cols': ['part_num', 'purch', 'refs'],  # Sort-order for online orders.
            'order_delimiter': ' ',  # Delimiter for online orders.
            # Formatting for distributor header in worksheet.
            'wrk_hdr_format': {
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#FF6600'  # Farnell/E14 orange.
            },
            # Web site defitions.
            'site': {
                'url': 'http://farnell.com/',
                'currency': 'USD',
                'locale': 'US'
            },
        }
    }
)
