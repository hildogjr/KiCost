#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) 2021 Salvador E. Tropea
# Copyright (c) 2021 Instituto Nacional de Tecnología Industrial
# License: Apache 2.0
# Project: KiCost
"""
Tool to generate the default exchange rates.
Should be used before each release.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from kicost.currency_converter.download_rates import download_rates

date, rates = download_rates()
assert date
print('#!/usr/bin/python3')
print('# -*- coding: utf-8 -*-')
print("default_date = '{}'".format(date))
first = True
for cur, rate in rates.items():
    cont = "'"+cur+"': "+str(rate)+","
    if first:
        first = False
        print("default_rates = {"+cont)
    else:
        print('                 '+cont)
print("                 }")
