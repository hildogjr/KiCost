# -*- coding: utf-8 -*-
# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Júnior
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

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

import os

# The distributor module directories will be found in this directory.
directory = os.path.dirname(__file__)

# Search for the distributor modules and import them.
for module in os.listdir(directory):

    # Avoid importing non distributors modules.
    # It should be placed at this folder and start with 'dist_'.
    abs_module = os.path.join(directory, module)
    if os.path.isdir(abs_module):
        continue
    if not os.path.basename(abs_module).startswith('dist_'):
        continue
    # Avoid directories like __pycache__.
    if module.startswith('__'):
        continue
    #TODO
    if module.startswith('dist_octo') or module.startswith('dist_local'):
        continue

    # Import the module.
    print('--------',module)
    tmp = __import__(module, globals(), locals(), [], level=1)
    tmp_mod = getattr(tmp, module);
    globals()["dist_"+module] = getattr(tmp_mod, "dist_"+module)

from .dist_octopart import * #TODO this should be programmetic and go inside the for above
from .dist_local_template import *


from .global_vars import distributor_dict

def init_distributor_dict():
    # Clear distributor_dict, then let all distributor modules recreate their entries.
    distributor_dict = {}
    for x in globals():
        if x.startswith("dist_"):
            globals()[x].dist_init_distributor_dict()

# Init distributor dict during import.
init_distributor_dict()
