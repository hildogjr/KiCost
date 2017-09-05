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
            'order_delimiter': ','
        }
    }
)
