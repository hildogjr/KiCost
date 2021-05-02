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
        # Distributor data
        self.part_num = {}  # Distributor catalogue number.
        self.url = {}  # Purchase distributor URL for the spefic part.
        self.price_tiers = {}  # Price break tiers; [[qty1, price1][qty2, price2]...]
        self.qty_avail = {}  # Available quantity.
        self.qty_increment = {}
        self.info_dist = {}
        self.currency = {}  # Default currency.
        self.moq = {}  # Minimum order quantity allowd by the distributor.
