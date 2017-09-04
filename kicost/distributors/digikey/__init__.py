# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

#from .digikey import get_digikey_price_tiers, get_digikey_part_num, get_digikey_qty_avail, get_digikey_part_html_tree
from . import digikey

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

