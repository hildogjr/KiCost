# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Junior / Max Maisel
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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()

from .. import distributor
from ..global_vars import distributor_dict

class dist_farnell(distributor.distributor):

    @staticmethod
    def dist_init_distributor_dict():
        distributor_dict.update({
            'farnell': {
                'octopart_name': 'Farnell',
                'module': 'farnell', # The directory name containing this file.
                'scrape': 'web',     # Allowable values: 'web' or 'local'.
                'label': 'Farnell',  # Distributor label used in spreadsheet columns.
                'order_cols': ['part_num', 'purch', 'refs'],  # Sort-order for online orders.
                'order_delimiter': ' ',  # Delimiter for online orders.
                # Formatting for distributor header in worksheet.
                'wrk_hdr_format': {
                    'font_size': 14,
                    'font_color': 'white',
                    'bold': True,
                    'align': 'center',
                    'valign': 'vcenter',
                    'bg_color': '#FF6600'  # Farnell/E14 orange.
                },
            }
        })
