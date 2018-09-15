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

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

import os

# The distributor module directories will be found in this directory.
directory = os.path.dirname(__file__)

# Search for the distributor modules and import them.
for module in os.listdir(directory):

    # Avoid importing non-directories.
    abs_module = os.path.join(directory, module)
    if not os.path.isdir(abs_module):
        continue

    # Avoid directories like __pycache__.
    if module.startswith('__'):
        continue

    # Import the module.
    tmp = __import__(module, globals(), locals(), [], level=1)
    tmp_mod = getattr(tmp, module);
    globals()["dist_"+module] = getattr(tmp_mod, "dist_"+module)

from .global_vars import distributor_dict

def init_distributor_dict():
    # Clear distributor_dict, then let all distributor modules recreate their entries.
    distributor_dict = {}
    for x in globals():
        if x.startswith("dist_"):
            globals()[x].dist_init_distributor_dict()

from .octopart import dist_octopart
from .local import dist_local

# Init distributor dict during import.
init_distributor_dict()
