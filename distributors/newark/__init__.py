# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

from .newark import *

# Place information about this distributor into the distributor dictionary.
from .. import distributors
distributors.update(
    {
        'newark': {
            'scrape': 'web',
            'label': 'Newark',
            'order_cols': ['part_num', 'purch', 'refs'],
            'order_delimiter': ',',
            'wrk_hdr_format': {
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#A2AE06'  # Newark/E14 olive green.
            }
        }
    }
)
