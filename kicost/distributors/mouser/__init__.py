# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

from .mouser import *

from .. import distributors
distributors.update(
    {
        'mouser': {
            'module': mouser,
            'scrape': 'web',
            'function': 'mouser',
            'label': 'Mouser',
            'order_cols': ['part_num', 'purch', 'refs'],
            'order_delimiter': ' '
        }
    }
)
