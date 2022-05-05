# -*- coding: utf-8 -*-

import logging

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'
# Export .version.__version__ as a module version
from .version import __version__, __build__  # noqa: F401

DEBUG_OVERVIEW = logging.DEBUG
DEBUG_DETAILED = logging.DEBUG-1
DEBUG_OBSESSIVE = logging.DEBUG-2
DEBUG_HTTP_HEADERS = logging.DEBUG-3
DEBUG_HTTP_RESPONSES = logging.DEBUG-4
DEBUG_FULL = logging.DEBUG-9
# Minimum possible log level is logging.DEBUG-9 !


class DistData(object):
    '''@brief Data from a distributor related to a part.'''
    def __init__(self):
        self.part_num = None  # Distributor catalogue number.
        self.url = None  # Purchase distributor URL for the spefic part.
        self.price_tiers = {}  # Price break tiers; [[qty1, price1][qty2, price2]...]
        self.qty_avail = None  # Available quantity.
        self.qty_increment = None
        # self.info_dist = None  # Currently unused.
        self.currency = None  # Default currency.
        self.moq = None  # Minimum order quantity allowd by the distributor.
        self.extra_info = {}


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
        self.dd = {}

    def update_specs(self, specs):
        for code, info in specs.items():
            name, value = info
            if code in self.specs:
                # Already here
                old_name, old_value = self.specs[code]
                if name not in old_name:
                    name = old_name + ', ' + name
                if old_value is not None and value not in old_value:
                    value = old_value + ', ' + value
            self.specs[code] = (name, value)


# The root logger of the application. This has to be the root logger to catch
# output from libraries (e.g. requests) as well.
main_logger = None


def debug(*args):
    main_logger.log(*args)


def debug_detailed(*args):
    main_logger.log(DEBUG_DETAILED, *args)


def is_debug_detailed():
    return main_logger.getEffectiveLevel() <= DEBUG_DETAILED


def debug_overview(*args):
    main_logger.log(DEBUG_OVERVIEW, *args)


def is_debug_overview():
    return main_logger.getEffectiveLevel() <= DEBUG_OVERVIEW


def debug_obsessive(*args):
    main_logger.log(DEBUG_OBSESSIVE, *args)


def is_debug_obsessive():
    return main_logger.getEffectiveLevel() <= DEBUG_OBSESSIVE


def debug_full(*args):
    main_logger.log(DEBUG_FULL, *args)


def debug_general(*args):
    main_logger.debug(*args)


def info(*args):
    main_logger.info(*args)


def warning(code, msg):
    main_logger.warning(code + msg)


def error(*args):
    main_logger.error(*args)


def get_logger():
    global main_logger
    return main_logger


def set_logger(logger):
    global main_logger
    main_logger = logger


class KiCostError(Exception):
    '''Exception for any error while running kicost().'''
    def __init__(self, msg, id):
        super(self.__class__, self).__init__(msg)
        self.msg = msg
        self.id = id
