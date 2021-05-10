#!/usr/bin/python3
# -*- coding: utf-8 -*-

# MIT license
#
# Copyright (c) 2020-2021 Salvador E. Tropea
# Copyright (c) 2020-2021 Instituto Nacional de Tecnología Industrial
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
Tool to generate the tables we need at runtime.
It uses the real babel package
"""
from babel import numbers  # For currency presentation.
from kicost.currency_converter.default_rates import default_rates

print('#!/usr/bin/python3')
print('# -*- coding: utf-8 -*-')
first = True
for currency in sorted(default_rates.keys()):
    if first:
        indent = 'currency_symbols = {'
        first = False
    else:
        indent = '                    '
    print(indent + "'{}': '{}',".format(currency, numbers.get_currency_symbol(currency, locale='en_US')))
print('                    }')
first = True
for currency in sorted(default_rates.keys()):
    if first:
        indent = 'currency_names = {'
        first = False
    else:
        indent = '                  '
    print(indent + "'{}': '{}',".format(currency, numbers.get_currency_name(currency, locale='en_US')))
print('                  }')
