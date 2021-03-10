#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) 2021 Salvador E. Tropea
# Copyright (c) 2021 Instituto Nacional de Tecnología Industrial
# License: Apache 2.0
# Project: KiCost
"""
A simple test for the CurrencyConverter class
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from kicost.currency_converter import CurrencyConverter


currency_convert = CurrencyConverter().convert
res = currency_convert(1, 'USD',  'EUR')
print('1 USD is {} EUR'.format(res))
