# -*- coding: utf-8 -*-

__author__='Giacinto Luigi Cerone'

from .farnell import *

# Place information about this distributor into the distributor dictionary.
from .. import distributors
distributors.update(
    {
        'farnell': {
            'scrape': 'web',
            'label': 'Farnell',
            'order_cols': ['part_num', 'purch', 'refs'],
            'order_delimiter': ' '
        }
    }
)

