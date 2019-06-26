# -*- coding: utf-8 -*-
# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Junior
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

# Heritage of the above global vars.
from ..global_vars import * # Debug information and `SEPRTR`.


# The global dictionary of distributor information starts out empty.
distributor_dict = {}
distributors_modules_dict = {}

# Extra informations to by got by each part in the distributors.
EXTRA_INFO_DIST = ['value', 'tolerance', 'footprint', 'power', 'current', 'voltage', 'frequency', 'temp_coeff', 'manf',
              'size', 'op temp', 'orientation', 'color',
              'datasheet', 'image', # Links.
             ]
extra_info_dist_name_translations = {
    #TODO it will need to put here language translation after implementation of ISSUE #65?
    'resistance': 'value',
    'inductance': 'value',
    'capacitance': 'value',
    'manufacturer': 'manf',
    'package': 'footprint',
    'package / case': 'footprint',
    'datasheets': 'datasheet',
    'dimension': 'size',
    'size / dimension': 'size',
    'operating temperature': 'op temp',
    'voltage - rated': 'voltage',
    'Mating Orientation': 'orientation',
    'coulor': 'color',
    'wire gauge': 'wire',
}
