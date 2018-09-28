# -*- coding: utf-8 -*-
# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo G Jr
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

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# The global dictionary of supported EDA tools starts out empty.
eda_dict = {}

import os

# The EDA tool directories will be found in this directory.
directory = os.path.dirname(__file__)

# Search for the EDA tool modules and import them.
eda_modules = {}
for module in os.listdir(directory):

    # Avoid importing non EDA class files.
    # It should be placed at this folder and start with 'eda_'.
    abs_module = os.path.join(directory, module)
    if os.path.isdir(abs_module):
        continue
    if not os.path.basename(abs_module).startswith('eda_'):
        continue
    # Avoid directories like __pycache__.
    if module.startswith('__'):
        continue

    # Import the module.
    #eda_modules[module] = __import__(module, globals(), locals(), [], level=1)

#TODO this should go inside the loop above and the file bellow should be translate to classes.
from .eda_kicad import *
from .eda_altium import *
from .eda_generic_csv import *
eda_modules['kicad'] = eda_kicad
eda_modules['altium'] = eda_altium
eda_modules['csv'] = eda_generic_csv
