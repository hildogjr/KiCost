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
from ..eda_tools.eda_tools import order_refs # To better print the warnings about the parts.

from . import fake_browser

import http.client # For web scraping exceptions.

from ..globals import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE # Debug configurations.
from ..globals import SEPRTR
from ..globals import PartHtmlError
from . import distributor_dict

import os, re

class distributor(object):
    start_time = time.time()
    def __init__(self, name, domain, scrape_retries, throttle_delay):
        self.name = name
        self.scrape_retries = scrape_retries
        self.logger = logger
        self.domain = domain

        # Don't create fake_browser for "local" distributor.
        if self.domain != None:
            self.browser = fake_browser.fake_browser \
                (self.domain, self.logger, self.scrape_retries, throttle_delay)

    # Abstract methods, implemented in distributor specific modules
    def dist_get_part_html_tree(self, pn, extra_search_terms, url, descend):
        raise NotImplementedError()

    def dist_get_part_num(self, html_tree):
        raise NotImplementedError()

    def dist_get_qty_avail(self, html_tree):
        raise NotImplementedError()

    def dist_get_price_tiers(self, html_tree):
        raise NotImplementedError()

    def dist_get_extra_info(self, html_tree):
        raise NotImplementedError()

    def dist_define_locale_currency(self, locale, currency):
        raise NotImplementedError()

    def define_locale_currency(self, locale_currency='USD'):
        '''@brief Configure the distributor for some locale/country and
        currency second ISO3166 and ISO4217
        
        @param `str` Alpha 2 country or alpha 3 currency or even one slash other.'''
        try:
            if distributor_dict[self.name]['scrape'] == 'web':
                # Not make sense to configurate a local distributor (yet).
                locale_currency = re.findall('\w{2,}', locale_currency)
                locale = None
                currency = None
                for alpha in locale_currency:
                    if len(alpha)==2:
                        locale = alpha
                    elif len(alpha)==3:
                        currency = alpha
                self.dist_define_locale_currency(locale, currency)
        except NotImplementedError:
            logger.warning('No currency/country configuration for {}.'.format(self.name))
            pass

    def scrape_part(self, id, part):
        '''@brief Scrape the data for a part from each distributor website or local HTML.
        
        Use distributors submodules to scrape each distributor part page and get
        informations such as price, quantity avaliable and others;
        
        @param `int` Count of the main loop.
        @param `str` String with the part number / distributor stock.
        @return id, distributor_name, url, `str` distributor stock part number,
            `dict` price tiers, `int` qty avail, `dict` extrainfo dist
        '''

        if multiprocessing.current_process().name == "MainProcess":
            self.logger = logging.getLogger('kicost')
        else:
            self.logger = multiprocessing.get_logger()
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(1)
            self.logger.addHandler(handler)
            self.logger.setLevel(1)
            self.browser.logger = self.logger

        url = {}
        part_num = {}
        qty_avail = {}
        price_tiers = {}
        info_dist = {}

        # Get the HTML tree for the part.
        html_tree, url = self.get_part_html_tree(part)

        # Call the functions that extract the data from the HTML tree.
        part_num = self.dist_get_part_num(html_tree)
        qty_avail = self.dist_get_qty_avail(html_tree)
        price_tiers = self.dist_get_price_tiers(html_tree)
        
        try:
            # Get extra characeristics of the part in the web page.
            # This will be use to comment in the 'cat#' column of the
            # spreadsheet and some validations (in the future implementaions)
            info_dist = self.dist_get_extra_info(html_tree)
        except:
            info_dist = {}
            pass

        # Return the part data.
        return id, self.name, url, part_num, price_tiers, qty_avail, info_dist

    def get_part_html_tree(self, part):
        '''@brief Get the HTML tree for a part.
        
        Get the HTML tree for a part from the given distributor website or local HTML.
        @param `str` part Part manufactor code or distributor stock code.
        @return `str` with the HTML webpage.'''

        self.logger.log(DEBUG_OBSESSIVE, 'Looking in %s by %s:', self.name, order_refs(part.refs, True))

        for extra_search_terms in set([part.fields.get('manf', ''), '']):
            try:
                # Search for part information using one of the following:
                #    1) the distributor's catalog number.
                #    2) the manufacturer's part number.
                for key in (self.name+'#', self.name+SEPRTR+'cat#', 'manf#'):
                    if key in part.fields:
                        if part.fields[key]:
                            self.logger.log(DEBUG_OBSESSIVE, "%s: scrape timing: %.2f" \
                                % (self.name, time.time() - distributor.start_time))
                            return self.dist_get_part_html_tree(part.fields[key], extra_search_terms)
                # No distributor or manufacturer number, so give up.
                else:
                    self.page_accessed = False
                    self.logger.warning("No '%s#' or 'manf#' field: cannot lookup part %s at %s.", \
                        self.name, part.refs, self.name)
                    return BeautifulSoup('<html></html>', 'lxml'), ''
                    #raise PartHtmlError
            except PartHtmlError:
                pass
            except AttributeError:
                break
        self.logger.warning("Part %s not found at %s.", order_refs(part.refs, False), self.name)
        # If no HTML page was found, then return a tree for an empty page.
        return BeautifulSoup('<html></html>', 'lxml'), ''


