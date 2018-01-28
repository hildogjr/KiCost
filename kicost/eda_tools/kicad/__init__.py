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

__author__ = 'XESS Corporation' # Improved by Hildo G Jr
__email__ = 'info@xess.com'

from .kicad import get_part_groups

# Place information about this EDA into the eda_tool dictionary.
from .. import eda_tool_dict
eda_tool_dict.update(
    {
        'kicad': {
            'module': 'kicad', # The directory name containing this file.
            'label': 'KiCad file', # Label used on the GUI.
            'desc': 'KiCad open source EDA.',
            # Formatting file match.
            'file': {
                'extension': '.xml', # File extension.
                'content': '<tool\>Eeschema.*\<\/tool\>' # Regular expression content match.
                }
        }
    }
)
