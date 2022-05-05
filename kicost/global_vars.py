# -*- coding: utf-8 -*-

# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Júnior
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

"""Stuff that everybody else needs to know about."""

PLATFORM_WINDOWS_STARTS_WITH = 'win32'
PLATFORM_LINUX_STARTS_WITH = 'linux'
PLATFORM_MACOS_STARTS_WITH = 'darwin'

SEPRTR = ':'  # Delimiter between library:component, distributor:field, etc.

# Default language used by GUI and spreadsheet generation and number presentation.
DEFAULT_LANGUAGE = 'en_US'
DEFAULT_CURRENCY = 'USD'  # Default currency assigned.

# Default maximum column width for the cell adjust
DEF_MAX_COLUMN_W = 32

# Error codes
ERR_INTERNAL = 1  # Unhandled exceptions
ERR_ARGS = 2  # Command line arguments
ERR_KICADCONFIG = 3  # An error related to KiCad configuration
ERR_KICOSTCONFIG = 4  # An error related to KiCost configuration
ERR_SCRAPE = 5  # Error trying to get prices
ERR_INPUTFILE = 6  # Error parsing input files
ERR_FIELDS = 7  # Some inconsistency with the fields

# Warning codes
W_TRANS = '(WC001) '  # Problem with field translate
W_NOMANP = '(WC002) '  # No manf# or distributor#
W_CONF = '(WC003) '  # Problem during --un/setup
W_NOPURCH = '(WC004) '  # No valid field for purchase
W_NOQTY = '(WC005) '  # No valid qty for purchase
W_ASSQTY = '(WC006) '  # Assigned qty during scrape
W_NOINFO = '(WC007) '  # No info during scrape
NO_PRICE = '(WC008) '  # No price during scrape
W_BADPRICE = '(WC009) '  # Some problem with the local price tier
W_FLDOVR = '(WC010) '  # Field overwrite
W_DUPWRONG = '(WC011) '  # Inconsistency in duplicated data
W_INCQTY = '(WC012) '  # Inconsistency in qty
W_REPMAN = '(WC013) '  # Asking to repeat a manufacturer
W_MANQTY = '(WC014) '  # Malformed manf#_qty
W_AMBIPN = '(WC015) '  # Ambiguous mpn, needs better manf
W_LOCFAIL = '(WC016) '  # Failed to set the locale
W_APIFAIL = '(WC017) '  # Failed to init an API
W_CONFIG = '(WC018) '  # Config file warning
W_CMDLINE = '(WC019) '  # Command line warning
W_NOAPI = '(WC020) '  # No API with this name

# Data types for the options common to various APIs
BASE_OP_TYPES = {'enable': bool, 'cache_ttl': (int, float), 'cache_path': str}


class wxPythonNotPresent(Exception):
    '''Exception for failed retrieval of an HTML parse tree for a part.'''
    pass
