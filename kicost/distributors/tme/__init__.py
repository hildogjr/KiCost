# -*- coding: utf-8 -*-

__author__ ='Adam Heinrich'
__email__ = 'adam@adamh.cz'

from .tme import *

# Place information about this distributor into the distributor dictionary.
from .. import distributor_dict
distributor_dict.update(
    {
        'tme': {
            'module': 'tme', # The directory name containing this file.
            'scrape': 'web',     # Allowable values: 'web' or 'local'.
            'label': 'TME',  # Distributor label used in spreadsheet columns.
            'order_cols': ['part_num', 'purch', 'refs'],  # Sort-order for online orders.
            'order_delimiter': ' ',  # Delimiter for online orders.
            # Formatting for distributor header in worksheet.
            'wrk_hdr_format': {
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#0C4DA1'  # TME blue
            },
            # Web site defitions.
            'site': {
            'url': 'https://www.tme.eu/en/',
            'currency': 'USD',
            'locale': 'UK'
            },
        }
    }
)
