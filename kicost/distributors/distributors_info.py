# -*- coding: utf-8 -*-
# This file keep all the web distributors information used by the different API/scrap modules.

# Author information.
__author__ = 'Hildo Guillardi Júnior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# Used as identification for all user fields allowed for some custom importation in some distributors.
# It is used a low probability "word" corresponding to all user fields.
ORDER_COL_USERFIELDS = '*__USER__FIELDS__*'
# TODO at the GUI, could be a tab with to personalize this configuration, using this file as default, and the user could include or exclude some
#      personal field.


class DistributorOrder(object):
    '''@brief Class to indicate how to place an order in a distributor.'''
    def __init__(self, url=None, cols=[], header=None, delimiter=',', replace_by_char='; ', not_allowed_char=',\n', info=None, limit=None):
        self.url = url
        # Sort-order fields for online orders. The not present fields are by-passed and `None` represent a empty column.
        self.cols = cols
        # Header to help user undertanding (used in some importations). **Currently unused**
        self.header = header
        # Delimiter for online orders.
        self.delimiter = delimiter
        # The `delimiter` is not allowed inside description. This character is used to replace it.
        self.replace_by_char = replace_by_char
        # Characters not allowed at the BoM for web-site import.
        self.not_allowed_char = not_allowed_char
        # Descriptive fields size limit
        self.limit = limit
        self.info = info


class DistributorLabel(object):
    '''@brief Class to describe a distributor column.'''
    def __init__(self, name, url, bg, fg='white'):
        self.name = name
        self.url = url
        # Formatting for distributor header in worksheet; bold, font and align are
        # `spreadsheet.py` defined but can by overload here.
        self.format = {'font_color': fg, 'bg_color': bg}


class DistributorInfo(object):
    '''@brief Class to describe a distributor.'''
    def __init__(self, order, label, type='web', ignore_cat=None):
        self.type = type   # Allowable values: 'local' or 'web'.
        self.order = order
        self.label = label
        # Regex used to ignore some catalogue/stock code format.
        # In the Digikey distributor it is used to ignore the Digi-reel package.
        self.ignore_cat = ignore_cat

    def is_local(self):
        return self.type == 'local'

    def is_web(self):
        return self.type == 'web'


distributors_info = {
    'arrow': DistributorInfo(
                order=DistributorOrder(
                    url='https://www.arrow.com/en/bom-tool/',
                    # header='Stock#,Quantity,Designators',
                    cols=['part_num', 'purch', 'refs']),
                label=DistributorLabel('Arrow', 'https://www.arrow.com/', '#000000')),  # Arrow black.
    'digikey': DistributorInfo(
                order=DistributorOrder(
                    url='https://www.digikey.com/ordering/shoppingcart',
                    # header='Quantity,Stock#,Designators',
                    cols=['purch', 'part_num', 'refs']),
                ignore_cat=r'.+(DKR\-ND|\-6\-ND)$',
                label=DistributorLabel('Digi-Key', 'https://www.digikey.com/', '#CC0000')),  # Digi-Key red.
    'farnell': DistributorInfo(
                order=DistributorOrder(
                    url='https://fr.farnell.com/en-FR/quick-order?isQuickPaste=true',
                    # header='Stock#,Quantity,Descriptions,Designators,',
                    cols=['part_num', 'purch', 'desc', 'refs'],
                    limit=30),
                label=DistributorLabel('Farnell', 'https://www.farnell.com/', '#FF6600')),  # Farnell/E14 orange.
    'mouser': DistributorInfo(
                order=DistributorOrder(
                    url='https://mouser.com/bom/',
                    # header='Stock#|Quantity|Designators',
                    cols=['part_num', 'purch', 'refs'],
                    delimiter='|',
                    not_allowed_char='| \n',
                    replace_by_char=';__'),
                label=DistributorLabel('Mouser', 'https://www.mouser.com/', '#004A85')),  # Mouser blue.
    'newark': DistributorInfo(
                order=DistributorOrder(
                    url='https://www.newark.com/quick-order?isQuickPaste=true',
                    # header='Stock#,Quantity,Designators,Descriptions,User',
                    cols=['part_num', 'purch', 'refs', 'desc']),
                label=DistributorLabel('Newark', 'https://www.newark.com/', '#A2AE06')),  # Newark/E14 olive green.
    'rs': DistributorInfo(
                order=DistributorOrder(
                    url='https://uk.rs-online.com/web/mylists/manualQuotes.html?method=showEnquiryCreationPage&mode=new',
                    # header='Stock#,Quantity,-,-,-,Part,Designators',
                    cols=['part_num', 'purch', None, None, None, 'manf#', 'refs']),  # `None` is used for generate a empty column.
                label=DistributorLabel('RS Components', 'https://uk.rs-online.com/', '#FF0000')),  # RS Components red.
    'tme': DistributorInfo(
                order=DistributorOrder(
                    url='https://www.tme.eu/en/Profile/QuickBuy/load.html',
                    # header='Stock# Quantity Designators',
                    cols=['part_num', 'purch', 'refs'],
                    delimiter=' ',
                    not_allowed_char=' \n',
                    replace_by_char=';'),
                label=DistributorLabel('TME', 'https://www.tme.eu/', '#0C4DA1')),  # TME blue.
    'lcsc': DistributorInfo(
                order=DistributorOrder(
                    url='https://lcsc.com/bom.html',
                    header='Quantity,Comment,Designator,Footprint,LCSC Part #(optional)',
                    cols=['purch', 'refs', 'footprint', 'part_num'],
                    info='Copy this header and order to a CSV\n'
                         'file and use it for JLCPCB \n'
                         'manufacturer PCB house.\n'
                         'The multipart components that use\n'
                         '"#" symbol are not allowed by JLCPCB.'),
                label=DistributorLabel('LCSC', 'https://lcsc.com/', '#1166DD')),  # LCSC blue.
    'local_template': DistributorInfo(
                type='local',
                order=DistributorOrder(cols=['part_num', 'purch', 'refs']),
                label=DistributorLabel('Local', None, '#008000')),  # Darker green.
}
