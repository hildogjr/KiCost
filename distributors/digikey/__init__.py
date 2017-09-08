# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

from .digikey import *

# Place information about this distributor into the distributor dictionary.
from .. import distributors
distributors.update(
    {
        'digikey': {
            'scrape': 'web',
            'label': 'Digi-Key',
            'order_cols': ['purch', 'part_num', 'refs'],
            'order_delimiter': ',',
            'wrk_hdr_format': {
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#CC0000'  # Digi-Key red.
            }
        }
    }
)

