# -*- coding: utf-8 -*-

__author__='Giacinto Luigi Cerone'

from .rs import *

# Place information about this distributor into the distributor dictionary.
from .. import distributor_dict
distributor_dict.update(
    {
        'rs': {
            'module': 'rs',           # The directory name containing this file.
            'scrape': 'web',          # Allowable values: 'web' or 'local'.
            'label': 'RS Components', # Distributor label used in spreadsheet columns.
            'order_cols': ['part_num', 'purch', 'refs'],  # Sort-order for online orders.
            'order_delimiter': ' ',  # Delimiter for online orders.
            # Formatting for distributor header in worksheet.
            'wrk_hdr_format': {
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#FF0000'  # RS Components red.
            },
            # Web site defitions.
            'site': {
                'url': 'http://rs-online.com/',
                'currency': 'USD',
                'locale': 'UK'
            },
        }
    }
)
