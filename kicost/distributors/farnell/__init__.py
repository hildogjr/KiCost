# -*- coding: utf-8 -*-

__author__='Giacinto Luigi Cerone'

from . import farnell

from .. import distributors
distributors.update(
    {
        'farnell': {
            'module': farnell,
            'scrape': 'web',
            'function': 'farnell',
            'label': 'Farnell',
            'order_cols': ['part_num', 'purch', 'refs'],
            'order_delimiter': ' '
        }
    }
)

