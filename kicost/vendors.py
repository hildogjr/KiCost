# MIT license
#
# Copyright (C) 2019 by XESS Corporation / Hildo Guillardi Júnior
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

from .global_vars import distributor_dict


def init_distributor_dict():
    # Clear distributor_dict, then let all distributor modules recreate their entries.
    distributor_dict = {}
    distributor_dict.update({
        'arrow': {
            'octopart_name': 'Arrow Electronics, Inc.',
            'module': 'arrow',   # The directory name containing this file.
            'type': 'api',     # Allowable values: 'api', 'scrap' or 'local'.
            'order': {
                'cols': ['part_num', 'purch', 'refs'],  # Sort-order for online orders.
                'delimiter': ',', # Delimiter for online orders.
                'not_allowed_char': ',', # Characters not allowed at the BoM for web-site import.
                'replace_by_char': ';', # The `delimiter` is not allowed inside description. This caracter is used to replace it.
            },
            'label': {
                'name': 'Arrow',  # Distributor label used in spreadsheet columns.
                # Formatting for distributor header in worksheet; bold, font and align are
                # `spreadsheet.py` defined but can by overload heve.
                'format': {'font_color': 'white', 'bg_color': '#000000'}, # Arrow black.
                'link': 'https://www.arrow.com/',
            },
        },
        'digikey': {
            'octopart_name': 'Digi-Key',
            'module': 'digikey',
            'type': 'api',
            'order': {
                'cols': ['purch', 'part_num', 'refs'],
                'delimiter': ',', 'not_allowed_char': ',', 'replace_by_char': ';',
            },
            'label': {
                'name': 'Digi-Key',
                'format': {'font_color': 'white', 'bg_color': '#CC0000'}, # Digi-Key red.
                'link': 'https://www.digikey.com/',
            },
        },
        'farnell': {
            'octopart_name': 'Farnell',
            'module': 'farnell',
            'type': 'api',
            'order': {
                'cols': ['part_num', 'purch', 'refs'],
                'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
            },
            'label': {
                'name': 'Farnell',
                'format': {'font_color': 'white', 'bg_color': '#FF6600'}, # Farnell/E14 orange.
                'link': 'https://www.newark.com/',
            },
        },
        'mouser': {
            'octopart_name': 'Mouser',
            'module': 'mouser', 
            'type': 'api',
            'order': {
                'cols': ['part_num', 'purch', 'refs'],
                'delimiter': '|', 'not_allowed_char': '| ', 'replace_by_char': ';_',
            },
            'label': {
                'name': 'Mouser', 
                'format': {'font_color': 'white', 'bg_color': '#004A85'}, # Mouser blue.
                'link': 'https://www.mouser.com',
            },
        },
        'newark': {
            'octopart_name': 'Newark',
            'module': 'newark',
            'type': 'api',
            'order': {
                'cols': ['part_num', 'purch', 'refs'],
                'delimiter': ',', 'not_allowed_char': ',', 'replace_by_char': ';',
            },
            'label': {
                'name': 'Newark',
                'format': {'font_color': 'white', 'bg_color': '#A2AE06'}, # Newark/E14 olive green.
                'link': 'https://www.newark.com/',
            },
        },
        'rs': {
            'octopart_name': 'RS Components',
            'module': 'rs',
            'type': 'api',
            'order': {
                'cols': ['part_num', 'purch', 'refs'],
                'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
            },
            'label': {
                'name': 'RS Components',
                'format': {'font_color': 'white', 'bg_color': '#FF0000'}, # RS Components red.
                'link': 'https://uk.rs-online.com/',
            },
        },
        'tme': {
            'octopart_name': 'TME',
            'module': 'tme',
            'type': 'api',
            'order': {
                'cols': ['part_num', 'purch', 'refs'],
                'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
            },
            'label': {
                'name': 'TME',
                'format': {'font_color': 'white', 'bg_color': '#0C4DA1'}, # TME blue
                'link': 'https://www.tme.eu',
            },
        },
    })