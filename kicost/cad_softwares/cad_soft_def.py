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

from .kicad import get_part_groups_kicad # Main function of this tool.
from .altium import get_part_groups_altium

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# Generate a dictionary to translate all the different ways people might want
# to refer to part numbers, vendor numbers, and such.
field_name_translations = {
    'mpn': 'manf#',
    'pn': 'manf#',
    'manf_num': 'manf#',
    'manf-num': 'manf#',
    'mfg_num': 'manf#',
    'mfg-num': 'manf#',
    'mfg#': 'manf#',
    'man_num': 'manf#',
    'man-num': 'manf#',
    'man#': 'manf#',
    'mnf_num': 'manf#',
    'mnf-num': 'manf#',
    'mnf#': 'manf#',
    'mfr_num': 'manf#',
    'mfr-num': 'manf#',
    'mfr#': 'manf#',
    'part-num': 'manf#',
    'part_num': 'manf#',
    'p#': 'manf#',
    'part#': 'manf#',
}
for stub in ['part#', '#', 'p#', 'pn', 'vendor#', 'vp#', 'vpn', 'num']:
    for dist in distributors:
        field_name_translations[dist + stub] = dist + '#'
        field_name_translations[dist + '_' + stub] = dist + '#'
        field_name_translations[dist + '-' + stub] = dist + '#'
field_name_translations.update(
    {
        'manf': 'manf',
        'manufacturer': 'manf',
        'mnf': 'manf',
        'man': 'manf',
        'mfg': 'manf',
        'mfr': 'manf',
    }
)
field_name_translations.update(
    {
        'variant': 'variant',
        'version': 'variant',
    }
)
field_name_translations.update(
    {
        'dnp': 'dnp',
        'nopop': 'dnp',
    }
)

if __name__=='__main__':
	field_name_translations()
