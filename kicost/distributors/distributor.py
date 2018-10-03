# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Max Maisel / Hildo Guillardi Júnior
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

# Author information.
__author__ = 'Max Maisel'
__webpage__ = 'https://github.com/mmmaisel/'

# Libraries.
import sys, time, os, re
import logging

#from . import fake_browser
#import http.client # For web scraping exceptions.
#from ..global_vars import PartHtmlError
# Kept this for future use.

from ..edas.tools import order_refs # To better print the warnings about the parts.

from .global_vars import distributor_dict
from ..global_vars import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE # Debug configurations.
from ..global_vars import SEPRTR

from currency_converter import CurrencyConverter

class distributor_class(object):
    start_time = time.time()
    def __init__(self, name, logger, output_currency='USD'):
        self.name = name
        self.logger = logger
        self.currency = output_currency

        # Don't create fake_browser for "local" distributor.
        #if self.domain != None:
        #    self.browser = fake_browser.fake_browser \
        #        (self.domain, self.logger, self.scrape_retries, throttle_delay)
        # Kept this for future use.


    def get_dist_parts_info(self, parts, distributors, currency_dst='USD'):
        ''' Get the parts info using the modules API/Scrape/Local.'''

        currency_dst = currency_dst.upper()
        def currency_converter_fun(value, currency):
            currency = ''.join(currency).upper()
            if currency and currency!=self.currency_output:
                try:
                    value = currency_convert(price, currency, currency)
                except:
                    pass
            return value
        #self.currency_converter = currency_converter_fun

        # Fill-in info for any locally-sourced parts not handled by Octopart.
        dist_local.dist_get_part_info(parts, distributors, currency)
        dist_octopart.query_part_info(parts, distributors, currency)

    # Abstract methods, implemented in distributor specific modules.
    @staticmethod
    def dist_init_distributor_dict():
        ''' Initialize and update the dictionary of the registered distributors classes.'''
        raise NotImplementedError()

    @staticmethod
    def query_part_info():
        ''' Get the parts info of one distributor class.'''
        raise NotImplementedError()
