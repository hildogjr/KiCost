# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

from .digikey import *

# Place information about this distributor into the distributor dictionary.
from .. import distributor_dict
distributor_dict.update(
    {
        'digikey': {
            'module': 'digikey', # The directory name containing this file.
            'scrape': 'web',     # Allowable values: 'web' or 'local'.
            'label': 'Digi-Key', # Distributor label used in spreadsheet columns.
            'order_cols': ['purch', 'part_num', 'refs'],  # Sort-order for online orders.
            'order_delimiter': ',',  # Delimiter for online orders.
            # Formatting for distributor header in worksheet.
            'wrk_hdr_format': {
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#CC0000'  # Digi-Key red.
            },
            # Web site defitions.
            'site': {
                'url': 'https://www.digikey.com',
                'currency': 'USD',
                'locale': 'US'
            },
        }
    }
)
