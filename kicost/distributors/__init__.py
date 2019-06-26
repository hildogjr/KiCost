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

from .global_vars import *


# Import and register here the API / local / scrape modules.

from .dist_local_template import * # Template for local distributors entry.
#from .api_octopart import *
from .api_partinfo_kitspace import *

distributors_modules_dict['dist_local_template'] = {'handle': dist_local_template}
#distributors_modules_dict['api_partinfo_kitspace'] = {'handle': api_octopart}
distributors_modules_dict['api_partinfo_kitspace'] = {'handle': api_partinfo_kitspace}

def init_distributor_dict():
    # Clear distributor_dict, then let all distributor modules recreate their entries.
    distributor_dict = {}
    for x in globals():
        if x.startswith("dist_") or x.startswith("api_") or x.startswith("scrape_"):
            globals()[x].init_dist_dict()
            # Import all "ditributors_templates" (`dist_`), APIs or scrape modules.

# Init distributor dict during import.
init_distributor_dict()
