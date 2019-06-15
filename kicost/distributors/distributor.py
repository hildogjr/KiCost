# -*- coding: utf-8 -*-

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

from .global_vars import *

from currency_converter import CurrencyConverter


__all__ = ['distributor_class']


class distributor_class(object):
    start_time = time.time()
    def __init__(self, name, logger):
        self.name = name
        self.logger = logger

        # Don't create fake_browser for "local" distributor.
        #if self.domain != None:
        #    self.browser = fake_browser.fake_browser \
        #        (self.domain, self.logger, self.scrape_retries, throttle_delay)
        # Kept this for future use.


    def get_dist_parts_info(self, parts, distributors, currency=DEFAULT_CURRENCY):
        ''' Get the parts info using the modules API/Scrape/Local.'''
        for d in distributors_modules:
            globals()[d].query_part_info(parts, distributors, currency)
            #dist_local_template.query_part_info(parts, distributors, currency)
           #api_partinfo_kitspace.query_part_info(parts, distributors, currency)

    # Abstract methods, implemented in distributor specific modules.
    @staticmethod
    def init_dist_dict():
        ''' Initialize and update the dictionary of the registered distributors classes.'''
        raise NotImplementedError()

    @staticmethod
    def query_part_info():
        ''' Get the parts info of one distributor class.'''
        raise NotImplementedError()
