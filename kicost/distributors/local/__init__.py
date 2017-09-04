# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

from .local import *

from .. import distributors
distributors.update(
    {
        'local_template': {
            'module': local,
            'scrape': 'web',
            'function': 'local',
            'label': 'Local',
            'order_cols': ['part_num', 'purch', 'refs'],
            'order_delimiter': ' '
        }
    }
)

