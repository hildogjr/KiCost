# MIT license
#
# Copyright (C) 2015 by XESS Corporation
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

#from .sub_parts import subpart_list, subpart_qty, subpart_part # To deal with subparts manufacture: components that need more than one component from distributor to be made.

# Libraries.
import re # Regular expression parser.

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# Definitions to parse the manufature / distributor code to allow
# sub parts and diferent quantities (even fraction) in these.

def subpart_list(part):
    # Get the list of sub parts manufacture / distributor code
    # numbers, these have to be separated by comma or semicolon.
    return re.split('(?<![\W\*\/])\s*[;,]\s*|\s*[;,]\s*(?![\W\*\/])',
                part.fields['manf#'])

def subpart_qty(subpart):
    # Get the quantity of the sub part manufacture / distributor
    # (pre-multiplicator).
    # e.g.: ' 4.5 * ADUM3150BRSZ-RL7' -> '4.5'
    # e.g.: '4/5  * ADUM3150BRSZ-RL7' -> '4/5'
    return len(re.findall('^([\d\.\/]+)\s*\*',
                sub_part_list))

def subpart_part(subpart):
    # Get the sub part manufacture / distributor number with out the
    # pre-multiplicator.
    # e.g.: ' 4.5 * ADUM3150BRSZ-RL7' -> 'ADUM3150BRSZ-RL7'
    # e.g.: '4/5 *  ADUM3150BRSZ-RL7' -> 'ADUM3150BRSZ-RL7'
    return re.findall('\**\s*([\d\w\_\-\+]+)$',
                sub_parts_each)
