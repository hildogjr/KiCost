# -*- coding: utf-8 -*- 
# This file keep all the web distributors information used by the different API/scrap modules.

# Author information.
__author__ = 'Hildo Guillardi Júnior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

distributors_info = {
    'arrow': {
        'type': 'web', # Allowable values: 'local' or 'web'.
        'order': {
            'cols': ['part_num', 'purch', 'refs'], # Sort-order for online orders.
            'delimiter': ',', # Delimiter for online orders.
            'not_allowed_char': ',', # Characters not allowed at the BoM for web-site import.
            'replace_by_char': ';', # The `delimiter` is not allowed inside description. This caracter is used to replace it.
        },
        'label': {
            'name': 'Arrow',  # Distributor label used in spreadsheet columns.
            # Formatting for distributor header in worksheet; bold, font and align are
            # `spreadsheet.py` defined but can by overload heve.
            'format': {'font_color': 'white', 'bg_color': '#000000'}, # Arrow black.
            'url': 'https://www.arrow.com/',
        },
    },
    'digikey': {
        'type': 'web',
        'order': {
            'url': 'https://www.digikey.com/ordering/shoppingcart',
            'cols': ['purch', 'part_num', 'refs'],
            'delimiter': ',', 'not_allowed_char': ',', 'replace_by_char': ';',
        },
        'label': {
            'name': 'Digi-Key',
            'format': {'font_color': 'white', 'bg_color': '#CC0000'}, # Digi-Key red.
            'url': 'https://www.digikey.com/',
        },
    },
    'farnell': {
        'type': 'web',
        'order': {
            'cols': ['part_num', 'purch', 'refs'],
            'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
        },
        'label': {
            'name': 'Farnell',
            'format': {'font_color': 'white', 'bg_color': '#FF6600'}, # Farnell/E14 orange.
            'url': 'https://www.newark.com/',
        },
    },
    'mouser': {
        'type': 'web',
        'order': {
            'cols': ['part_num', 'purch', 'refs'],
            'delimiter': '|', 'not_allowed_char': '| ', 'replace_by_char': ';_',
        },
        'label': {
            'name': 'Mouser', 
            'format': {'font_color': 'white', 'bg_color': '#004A85'}, # Mouser blue.
            'url': 'https://www.mouser.com',
        },
    },
    'newark': {
        'type': 'web',
        'order': {
            'cols': ['part_num', 'purch', 'refs'],
            'delimiter': ',', 'not_allowed_char': ',', 'replace_by_char': ';',
        },
        'label': {
            'name': 'Newark',
            'format': {'font_color': 'white', 'bg_color': '#A2AE06'}, # Newark/E14 olive green.
            'url': 'https://www.newark.com/',
        },
    },
    'rs': {
        'type': 'web',
        'order': {
            'cols': ['part_num', 'purch', 'refs'],
            'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
        },
        'label': {
            'name': 'RS Components',
            'format': {'font_color': 'white', 'bg_color': '#FF0000'}, # RS Components red.
            'url': 'https://uk.rs-online.com/',
        },
    },
    'tme': {
        'type': 'web',
        'order': {
            'cols': ['part_num', 'purch', 'refs'],
            'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
        },
        'label': {
            'name': 'TME',
            'format': {'font_color': 'white', 'bg_color': '#0C4DA1'}, # TME blue
            'url': 'https://www.tme.eu',
        },
    },
}