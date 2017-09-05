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
            'order_delimiter': ' '
        }
    }
)
