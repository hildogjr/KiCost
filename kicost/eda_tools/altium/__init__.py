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

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

from .altium import get_part_groups

# Place information about this EDA into the eda_tool dictionary.
from .. import eda_tool_dict
eda_tool_dict.update(
    {
        'altium': {
            'module': 'altium', # The directory name containing this file.
            'label': 'Altium file', # Label used on the GUI.
            'desc': 'Altium Limited (formerly known as Protel until 2001).',
            # Formatting file match .
            'file': {
                'extension': '.xml', # File extension.
                'content': '\<GRID[\s\S]+<COLUMNS>[\s\S]+<COLUMN[\s\S]+<\/COLUMNS>[\s\S]+<ROWS>[\s\S]+\<ROW[\s\S]+\<\/ROWS>[\s\S]+\<\/GRID>' # Regular expression content match.
            }
        }
    }
)
