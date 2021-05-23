# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'
# Export .version.__version__ as a module version
from .version import __version__  # noqa: F401


# Class for storing part group information.
class PartGroup(object):
    '''@brief Class to group components.'''
    def __init__(self):
        # None by default, here to avoid try/except in the code
        self.datasheet = None
        self.lifecycle = None
        self.specs = {}  # Miscellaneous data from the queries
        # Distributor data
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

