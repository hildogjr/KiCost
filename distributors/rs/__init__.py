# -*- coding: utf-8 -*-

__author__='Giacinto Luigi Cerone'

from .rs import *

# Place information about this distributor into the distributor dictionary.
from .. import distributors
distributors.update(
    {
        'rs': {
            'scrape': 'web',
            'label': 'RS Components',
            'order_cols': ['part_num', 'purch', 'refs'],
            'order_delimiter': ' ',
            'wrk_hdr_format': {
                'font_size': 14,
                'font_color': 'white',
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#FF0000'  # RS Components red.
            }
        }
    }
)
