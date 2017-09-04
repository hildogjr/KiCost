# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

from .digikey import *

from .. import distributors
distributors.update(
    {
        'digikey': {
            'module': digikey,
            'scrape': 'web',
            'function': 'digikey',
            'label': 'Digi-Key',
            'order_cols': ['purch', 'part_num', 'refs'],
            'order_delimiter': ','
        }
    }
)

