# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

from .local import *

# Place information about this distributor into the distributor dictionary.
from .. import distributor_dict
distributor_dict.update(
    {
        'local_template': {
            'module': 'local', # The directory name containing this file.
            'scrape': 'local', # Allowable values: 'web' or 'local'.
            'label': 'Local',  # Distributor label used in spreadsheet columns.
            'order_cols': ['part_num', 'purch', 'refs'],  # Sort-order for online orders.
            'order_delimiter': ' ',  # Delimiter for online orders.
            # Formatting for distributor header in worksheet.
            'wrk_hdr_format': {
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#008000'  # Darker green.
            },
        }
    }
)
