# -*- coding: utf-8 -*-

__author__='Giacinto Luigi Cerone'

from . import rs

from ..kicost import distributors
distributors.update(
    {
        'rs': {
            'module': rs,
            'scrape': 'web',
            'function': 'rs',
            'label': 'RS Components',
            'order_cols': ['part_num', 'purch', 'refs'],
            'order_delimiter': ' '
        }
    }
)
