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

# Inserted by Pasteurize tool.
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from builtins import zip, range, int, str
from future import standard_library
standard_library.install_aliases()

import future

import re, difflib
from bs4 import BeautifulSoup
import http.client # For web scraping exceptions.
from .. import urlencode, urlquote, urlsplit, urlunsplit
from .. import fake_browser
from ...globals import PartHtmlError
from ...globals import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE
from currency_converter import CurrencyConverter
currency = CurrencyConverter()


def get_price_tiers(html_tree):
    '''@brief Get the pricing tiers from the parsed tree of the RS Components product page.
       @param html_tree `str()` html of the distributor part page.
       @return `dict()` price breaks, the keys are the quantities breaks.
    '''
    price_tiers = {}
    
    try:
        for row in html_tree.find_all('div', class_='table-row value-row'):
            qty = row.find('div',
                        class_='breakRangeWithoutUnit col-xs-4').text
            price = row.find('div',
                        class_='unitPrice col-xs-4').text
            try:
                qty = int( re.findall('\s*([0-9\,]+)', qty)[0] )
                price = re.sub('[^0-9\.]', '', price.replace(',','.') )
                price = currency.convert(float(price), 'EUR', 'USD')
                price_tiers[qty] = price
            except (TypeError, AttributeError, ValueError):
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        return price_tiers  # Return empty price tiers.
    return price_tiers
    
def get_part_num(html_tree):
    '''@brief Get the part number from the RS product page.
       @param html_tree `str()` html of the distributor part page.
       @return `dict()` price breaks, the keys are the quantities breaks.
    '''
    try:
        pn_str = html_tree.find('span', class_='keyValue').text
        pn = re.sub('[^0-9\-]','', pn_str)
        return pn
    except KeyError:
        return '' # No catalog number found in page.
    except AttributeError:
        return '' # No ProductDescription found in page.

def get_qty_avail(html_tree):
    '''Get the available quantity of the part from the RS product page.
       @param html_tree `str()` html of the distributor part page.
       @return `int` avaliable quantity.
    '''
        
    try:
        # Note that 'availability' is misspelled in the container class name!        
        qty_str = html_tree.find('span', class_=('stock-msg-content', 'table-cell')).text
    except (AttributeError, ValueError):
        # No quantity found (not even 0) so this is probably a non-stocked part.
        # Return None so the part won't show in the spreadsheet for this dist.
        return None
    try:
        qty = re.sub('[^0-9]','',qty_str[0:10])  # Strip all non-number chars.
        return int(qty)  # Return integer for quantity.
    except ValueError:
        # No quantity found (not even 0) so this is probably a non-stocked part.
        # Return None so the part won't show in the spreadsheet for this dist.
        return None

def get_part_html_tree(dist, pn, extra_search_terms='', url=None, descend=2, local_part_html=None, scrape_retries=2):
    '''@brief Find the RS Components HTML page for a part number and return the URL and parse tree.
       @param dist
       @param pn Part number `str()`.
       @param extra_search_terms
       @param url
       @param descend
       @param local_part_html
       @param scrape_retries `int` Quantity of retries in case of fail.
       @return (html `str()` of the page, url)
    '''
            
    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://it.rs-online.com/web/c/?searchTerm=' + urlquote(pn + ' ' + extra_search_terms, safe='')

    elif url[0] == '/':
        url = 'http://it.rs-online.com' + url
    elif url.startswith('..'):
        url = 'http://it.rs-online.com/Search/' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    try:
        html = fake_browser(url, scrape_retries)
    except:
        logger.log(DEBUG_OBSESSIVE,'No HTML page for {} from {}'.format(pn, dist))
        raise PartHtmlError

    try:
        tree = BeautifulSoup(html, 'lxml')
    except Exception:
        logger.log(DEBUG_OBSESSIVE,'No HTML tree for {} from {}'.format(pn, dist))
        raise PartHtmlError

    # Abort if the part number isn't in the HTML somewhere.
    # (Only use the numbers and letters to compare PN to HTML.)
    if re.sub('[\W_]','',str.lower(pn)) not in re.sub('[\W_]','',str.lower(str(html))):
        logger.log(DEBUG_OBSESSIVE,'No part number {} in HTML page from {}'.format(pn, dist))
        raise PartHtmlError
        
    # If the tree contains the tag for a product page, then just return it.
    if tree.find('div', class_='advLineLevelContainer'):
        return tree, url

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('div', class_=('resultsTable','results-table-container')) is not None:
        logger.log(DEBUG_OBSESSIVE,'Found product table for {} from {}'.format(pn, dist))
        if descend <= 0:
            logger.log(DEBUG_OBSESSIVE,'Passed descent limit for {} from {}'.format(pn, dist))
            raise PartHtmlError
        else:
            # Look for the table of products.
            products = tree.find('table', id='results-table').find_all(
                    'tr', class_='resultRow')

            # Extract the product links for the part numbers from the table.
            product_links = [p.find('a', class_='product-name').get('href') for p in products]

            # Extract all the part numbers from the text portion of the links.
            part_numbers = [p.find('span', class_='text-contents').get_text() for p in products]

            # Look for the part number in the list that most closely matches the requested part number.
            match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]

            # Now look for the link that goes with the closest matching part number.
            for i in range(len(product_links)):
                if part_numbers[i] == match:
                    # Get the tree for the linked-to page and return that.
                    logger.log(DEBUG_OBSESSIVE,'Selecting {} from product table for {} from {}'.format(part_numbers[i], pn, dist))
                    return get_part_html_tree(dist, pn, extra_search_terms,
                                              url=product_links[i],
                                              descend=descend-1,
                                              scrape_retries=scrape_retries)

    # I don't know what happened here, so give up.
    logger.log(DEBUG_OBSESSIVE,'Unknown error for {} from {}'.format(pn, dist))
    raise PartHtmlError
