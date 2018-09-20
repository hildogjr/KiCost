# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Max Maisel
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
import sys
from bs4 import BeautifulSoup # XML file interpreter.
import multiprocessing # To deal with the parallel scrape.
import logging
import time
from random import choice

from .global_vars import distributor_dict
from . import fake_browser

from ..eda_tools.eda_tools import order_refs # To better print the warnings about the parts.

import http.client # For web scraping exceptions.

from ..global_vars import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE # Debug configurations.
from ..global_vars import SEPRTR
from ..global_vars import PartHtmlError

import os, re
from currency_converter import CurrencyConverter


class distributor(object):
    start_time = time.time()
    def __init__(self, name, domain, scrape_retries, throttle_delay):
        self.name = name
        self.scrape_retries = scrape_retries
        self.logger = logger
        self.domain = domain
        self.currency_converter = CurrencyConverter().convert

        # Don't create fake_browser for "local" distributor.
        if self.domain != None:
            self.browser = fake_browser.fake_browser \
                (self.domain, self.logger, self.scrape_retries, throttle_delay)

    # Abstract methods, implemented in distributor specific modules.
    @staticmethod
    def dist_init_distributor_dict():
        raise NotImplementedError()

    
