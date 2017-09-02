# MIT license
#
# Copyright (C) 2015 by XESS Corporation
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

# Inserted by Pasteurize tool.
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from builtins import zip
from builtins import range
from builtins import int
from builtins import str
from future import standard_library
standard_library.install_aliases()

import future

import re
import logging
from bs4 import BeautifulSoup
import http.client # For web scraping exceptions.

try:
    from urllib.parse import urlencode, quote as urlquote, urlsplit, urlunsplit
    import urllib.request
    from urllib.request import urlopen, Request
except ImportError:
    from urlparse import quote as urlquote, urlsplit, urlunsplit
    from urllib import urlencode
    from urllib2 import urlopen, Request

from ..kicost import PartHtmlError, FakeBrowser
from ..kicost import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE

from currency_converter import CurrencyConverter

SEPRTR = ':'  # Delimiter between library:component, distributor:field, etc.

HTML_RESPONSE_RETRIES = 2 # Num of retries for getting part data web page.

WEB_SCRAPE_EXCEPTIONS = (urllib.request.URLError, http.client.HTTPException)


def get_local_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the local product page.'''
    price_tiers = {}
    try:
        pricing = html_tree.find('div', class_='pricing').text
        pricing = re.sub('[^0-9.;:]', '', pricing) # Keep only digits, decimals, delimiters.
        for qty_price in pricing.split(';'):
            qty, price = qty_price.split(SEPRTR)
            price_tiers[int(qty)] = float(price)
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        logger.log(DEBUG_OBSESSIVE, 'No local pricing information found!')
        return price_tiers  # Return empty price tiers.
    return price_tiers


def get_local_part_num(html_tree):
    '''Get the part number from the local product page.'''
    try:
        part_num_str = html_tree.find('div', class_='cat#').text
        return part_num_str
    except AttributeError:
        return ''


def get_local_qty_avail(html_tree):
    '''Get the available quantity of the part from the local product page.'''
    try:
        qty_str = html_tree.find('div', class_='quantity').text
    except (AttributeError, ValueError):
        # Return 0 (not None) so this part will show in the spreadsheet
        # even if there is no quantity found.
        return 0
    try:
        return int(re.sub('[^0-9]', '', qty_str))
    except ValueError:
        # Return 0 (not None) so this part will show in the spreadsheet
        # even if there is no quantity found.
        logger.log(DEBUG_OBSESSIVE, 'No local part quantity found!')
        return 0


def get_local_part_html_tree(dist, pn, extra_search_terms='', url=None, local_part_html=None):
    '''Extract the HTML tree from the HTML page for local parts.'''

    # Extract the HTML tree from the local part HTML page.
    try:
        tree = BeautifulSoup(local_part_html, 'lxml')
    except Exception:
        raise PartHtmlError

    try:
        # Find the DIV in the tree for the given part and distributor.
        class_ = dist + SEPRTR + pn
        part_tree = tree.find('div', class_=class_)
        url_tree = part_tree.find('div', class_='link')
        try:
            # Return the part data tree and any URL associated with the part.
            return part_tree, url_tree.text.strip()
        except AttributeError:
            # Return part data tree and None if the URL is not found.
            return part_tree, None
    except AttributeError:
        # Return an error if the part_tree is not found.
        raise PartHtmlError
