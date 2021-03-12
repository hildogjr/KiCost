# -*- coding: utf-8 -*- 
# This file keep all the web distributors information used by the different API/scrap modules.

# Author information.
__author__ = 'Hildo Guillardi Júnior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

ORDER_COL_USERFIELDS = '*__USER__FIELDS__*' # Used as identification for all user fields allowed for some custom importation in some distributors. It is used a low probability "word" corresponding to all user fields.
#TODO at the GUI, could be a tab with to personalize this configuration, using this file as default, and the user could include or exclude some personal field.

distributors_info = {
    'arrow': {
        'type': 'web', # Allowable values: 'local' or 'web'.
        'order': {
            'url': 'https://www.arrow.com/en/bom-tool/',
            'cols': ['part_num', 'purch', 'refs'], # Sort-order fields for online orders. The not present fields are by-passed and `None` represent a empty column.
            #'header': 'Stock#,Quantity,Designators', # Header to help user undertanding (used in some importations).
            'delimiter': ',', # Delimiter for online orders.
            'not_allowed_char': ',', # Characters not allowed at the BoM for web-site import.
            'replace_by_char': ';', # The `delimiter` is not allowed inside description. This character is used to replace it.
        },
        'label': {
            'name': 'Arrow', 'url': 'https://www.arrow.com/', # Distributor label used in spreadsheet columns.
            # Formatting for distributor header in worksheet; bold, font and align are
            # `spreadsheet.py` defined but can by overload here.
            'format': {'font_color': 'white', 'bg_color': '#000000'}, # Arrow black.
        },
    },
    'digikey': {
        'type': 'web',
        'order': {
            'url': 'https://www.digikey.com/ordering/shoppingcart',
            'cols': ['purch', 'part_num', 'refs'],
            #'header': 'Quantity,Stock#,Designators',
            'delimiter': ',', 'not_allowed_char': ',', 'replace_by_char': ';',
        },
        'label': {
            'name': 'Digi-Key', 'url': 'https://www.digikey.com/',
            'format': {'font_color': 'white', 'bg_color': '#CC0000'}, # Digi-Key red.
        },
        'ignore_cat#_re': r'.+(DKR\-ND|\-6\-ND)$', # Use to ignore some catalogue/stock code format. In the Digikey distributor it is used to ignore the Digi-reel package.
    },
    'farnell': {
        'type': 'web',
        'order': {
            'url': 'https://www.newark.com/quick-order?isQuickPaste=true',
            'cols': ['part_num', 'purch', 'refs', 'desc', ORDER_COL_USERFIELDS],
            #'header': 'Stock#,Quantity,Designators,Descriptions,User',
            'delimiter': ',', 'not_allowed_char': [',','\n'], 'replace_by_char': ';',
        },
        'label': {
            'name': 'Farnell', 'url': 'https://www.newark.com/',
            'format': {'font_color': 'white', 'bg_color': '#FF6600'}, # Farnell/E14 orange.
        },
    },
    'mouser': {
        'type': 'web',
        'order': {
            'url': 'https://mouser.com/bom/',
            'cols': ['part_num', 'purch', 'refs'],
            #'header': 'Stock#|Quantity|Designators',
            'delimiter': '|', 'not_allowed_char': '| ', 'replace_by_char': ';_',
        },
        'label': {
            'name': 'Mouser', 'url': 'https://www.mouser.com',
            'format': {'font_color': 'white', 'bg_color': '#004A85'}, # Mouser blue.
        },
    },
    'newark': {
        'type': 'web',
        'order': {
            'url': 'https://www.newark.com/quick-order?isQuickPaste=true',
            'cols': ['part_num', 'purch', 'refs', 'desc', ORDER_COL_USERFIELDS],
            #'header': 'Stock#,Quantity,Designators,Descriptions,User',
            'delimiter': ',', 'not_allowed_char': [',','\n'], 'replace_by_char': ';',
        },
        'label': {
            'name': 'Newark', 'url': 'https://www.newark.com/',
            'format': {'font_color': 'white', 'bg_color': '#A2AE06'}, # Newark/E14 olive green.
        },
    },
    'rs': {
        'type': 'web',
        'order': {
            'url': 'https://uk.rs-online.com/web/mylists/manualQuotes.html?method=showEnquiryCreationPage&mode=new',
            'cols': ['part_num', 'purch', None, None, None, 'manf#', 'refs'], # `None` is used for generate a empty column.
            #'header': 'Stock# Quantity Designators',
            'delimiter': ',', 'not_allowed_char': ',', 'replace_by_char': ';',
        },
        'label': {
            'name': 'RS Components', 'url': 'https://uk.rs-online.com/',
            'format': {'font_color': 'white', 'bg_color': '#FF0000'}, # RS Components red.
        },
    },
    'tme': {
        'type': 'web',
        'order': {
            'url': 'https://www.tme.eu/en/Profile/QuickBuy/load.html',
            'cols': ['part_num', 'purch', 'refs'],
            #'header': 'Stock# Quantity Designators',
            'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
        },
        'label': {
            'name': 'TME', 'url': 'https://www.tme.eu',
            'format': {'font_color': 'white', 'bg_color': '#0C4DA1'}, # TME blue.
        },
    },
    'lcsc': {
        'type': 'web',
        'order': {
            'url': 'https://lcsc.com/bom.html',
            'cols': ['purch', 'refs', 'footprint', 'part_num'],
            'header': 'Quantity,Comment,Designator,Footprint,LCSC Part #(optional)',
            'delimiter': ',', 'not_allowed_char': ',', 'replace_by_char': ';',
            'info': 'Copy this header and order to CSV file and use for JLCPCB manufacture PCB housing. The multipart components that use "#" symbol is not allowed at JLCPCB.',
        },
        'label': {
            'name': 'LCSC', 'url': 'https://lcsc.com',
            'format': {'font_color': 'white', 'bg_color': '#1166DD'}, # LCSC blue.
        },
    },
}