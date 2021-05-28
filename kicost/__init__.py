# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'
# Export .version.__version__ as a module version
from .version import __version__, __build__  # noqa: F401


# Class for storing part group information.
class PartGroup(object):
    '''@brief Class to group components.'''
    def __init__(self):
        # None by default, here to avoid try/except in the code
        self.datasheet = None
        self.lifecycle = None
        self.specs = {}  # Miscellaneous data from the queries
        self.min_price = None  # Filled by the spreadsheet code, expressed in the main currency
        # Values derived from manf#_qty
        self.qty = None  # Quantity for each project, just a number if only 1 project
        self.qty_str = None  # Formulas to compute the quantity in the spreadsheet
        self.qty_total_spreadsheet = 0  # Total quantity for all projects for the spreadsheet
        # Distributor data
        # TODO: distributor data should be a class and we should have a hash dist -> data
        self.part_num = {}  # Distributor catalogue number.
        self.url = {}  # Purchase distributor URL for the spefic part.
        self.price_tiers = {}  # Price break tiers; [[qty1, price1][qty2, price2]...]
        self.qty_avail = {}  # Available quantity.
        self.qty_increment = {}
        self.info_dist = {}  # Currently unused.
        self.currency = {}  # Default currency.
        self.moq = {}  # Minimum order quantity allowd by the distributor.

    def update_specs(self, specs):
        for code, info in specs.items():
            name, value = info
            if code in self.specs:
                # Already here
                old_name, old_value = self.specs[code]
                if name not in old_name:
                    name = old_name + ', ' + name
                if value not in old_value:
                    value = old_value + ', ' + value
            self.specs[code] = (name, value)
