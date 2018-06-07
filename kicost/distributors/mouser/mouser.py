# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Junior / Max Maisel
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
from __future__ import print_function, unicode_literals, division, absolute_import
from builtins import zip, range, int, str
from future import standard_library
standard_library.install_aliases()
import future

import re, difflib
from bs4 import BeautifulSoup
import http.client # For web scraping exceptions.
from .. import fake_browser
from ...globals import PartHtmlError
from ...globals import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE, DEBUG_HTTP_RESPONSES

from .. import distributor, distributor_dict

from urllib.parse import quote_plus as urlquote

class dist_mouser(distributor.distributor):
    def __init__(self, name, scrape_retries, throttle_delay):
        super(dist_mouser, self).__init__(name, distributor_dict[name]['site']['url'],
            scrape_retries, throttle_delay)
        self.browser.add_cookie('.mouser.com', 'preferences', 'ps=www2&pl=en-US&pc_www2=USDe')

    def dist_get_price_tiers(self, html_tree):
        '''@brief Get the pricing tiers from the parsed tree of the Mouser product page.
           @param html_tree `str()` html of the distributor part page.
           @return `dict()` price breaks, the keys are the quantities breaks.
        '''
        price_tiers = {}
        try:
            pricing_tbl_tree = html_tree.find('div', class_='pdp-pricing-table')
            price_row_trees = pricing_tbl_tree.find_all('div', class_='div-table-row')
            for row_tree in price_row_trees:
                qty_tree, unit_price_tree, _ = row_tree.find('div', class_='row').find_all('div', class_='col-xs-4')
                try:
                    qty = int(re.sub('[^0-9]', '', qty_tree.text))
                    unit_price = float(re.sub('[^0-9.]', '', unit_price_tree.text))
                    price_tiers[qty] = unit_price
                except ValueError:
                    pass # In case of "quote price", ignore and pass to next (check pn STM32F411RCT6).
            return price_tiers

            qty_strs = []
            for qty in html_tree.find('div',
                                      class_='PriceBreaks').find_all(
                                          'div',
                                          class_='PriceBreakQuantity'):
                qty_strs.append(qty.text)
            price_strs = []
            for price in html_tree.find('div',
                                        class_='PriceBreaks').find_all(
                                            'div',
                                            class_='PriceBreakPrice'):
                price_strs.append(price.text)
            qtys_prices = list(zip(qty_strs, price_strs))
            for qty_str, price_str in qtys_prices:
                try:
                    qty = re.search('(\s*)([0-9,]+)', qty_str).group(2)
                    qty = int(re.sub('[^0-9]', '', qty))
                    price_tiers[qty] = float(re.sub('[^0-9\.]', '', price_str))
                except (TypeError, AttributeError, ValueError, IndexError):
                    continue
        except AttributeError:
            # This happens when no pricing info is found in the tree.
            self.logger.log(DEBUG_OBSESSIVE, 'No Mouser pricing information found!')
            return price_tiers  # Return empty price tiers.
        return price_tiers

    def dist_get_part_num(self, html_tree):
        '''@brief Get the part number from the Mouser product page.
           @param html_tree `str()` html of the distributor part page.
           @return `list()`of the parts that match.
        '''
        try:
            partnum = html_tree.find(
                            'span', id='spnMouserPartNumFormattedForProdInfo'
                            ).text
            return partnum.strip()
        except AttributeError:
            self.logger.log(DEBUG_OBSESSIVE, 'No Mouser part number found!')
            return ''

    def dist_get_qty_avail(self, html_tree):
        '''@brief Get the available quantity of the part from the Mouser product page.
           @param html_tree `str()` html of the distributor part page.
           @return `int` avaliable quantity.
        '''
        try:
            qty_str = html_tree.find(
                                    'div', class_='pdp-product-availability').find(
                                    'div', class_='row').find(
                                    'div', class_='col-xs-8').find('div').text
        except AttributeError as e:
            # No quantity found (not even 0) so this is probably a non-stocked part.
            # Return None so the part won't show in the spreadsheet for this dist.
            self.logger.log(DEBUG_OBSESSIVE, 'No Mouser part quantity found!')
            return None
        try:
            qty_str = re.search('(\s*)([0-9,]*)', qty_str, re.IGNORECASE).group(2)
            return int(re.sub('[^0-9]', '', qty_str))
        except ValueError:
            # No quantity found (not even 0) so this is probably a non-stocked part.
            # Return None so the part won't show in the spreadsheet for this dist.
            self.logger.log(DEBUG_OBSESSIVE, 'No Mouser part quantity found!')
            return None

    def dist_get_part_html_tree(self, pn, extra_search_terms='', url=None, descend=2):
        '''@brief Find the Mouser HTML page for a part number and return the URL and parse tree.
           @param pn Part number `str()`.
           @param extra_search_terms
           @param url
           @param descend
           @return (html `str()` of the page, url)
        '''

        # Use the part number to lookup the part using the site search function, unless a starting url was given.
        if url is None:
            url = 'https://www.mouser.com/Search/Refine.aspx?Keyword=' + urlquote(pn, safe='')
            if extra_search_terms:
                url = url + urlquote(' ' + extra_search_terms, safe='')
        elif url[0] == '/':
            url = 'https://www.mouser.com' + url
        elif url.startswith('..'):
            url = 'https://www.mouser.com/Search/' + url

        # Open the URL, read the HTML from it, and parse it into a tree structure.
        try:
            html = self.browser.scrape_URL(url)
        except Exception as ex:
            self.logger.log(DEBUG_OBSESSIVE,'No HTML page for {} from {}'.format(pn, self.name))
            raise PartHtmlError

        # Abort if the part number isn't in the HTML somewhere.
        # (Only use the numbers and letters to compare PN to HTML.)
        if re.sub('[\W_]','',str.lower(pn)) not in re.sub('[\W_]','',str.lower(str(html))):
            self.logger.log(DEBUG_OBSESSIVE,'No part number {} in HTML page from {}'.format(pn, self.name))
            raise PartHtmlError
        
        try:
            tree = BeautifulSoup(html, 'lxml')
        except Exception:
            self.logger.log(DEBUG_OBSESSIVE,'No HTML tree for {} from {}'.format(pn, self.name))
            raise PartHtmlError

        # If the tree contains the tag for a product page, then just return it.
        if tree.find('div', id='pdpPricingAvailability') is not None:
            return tree, url

        # If the tree is for a list of products, then examine the links to try to find the part number.
        if tree.find('div', id='searchResultsTbl') is not None:
            self.logger.log(DEBUG_OBSESSIVE,'Found product table for {} from {}'.format(pn, self.name))
            if descend <= 0:
                self.logger.log(DEBUG_OBSESSIVE,'Passed descent limit for {} from {}'.format(pn, self.name))
                raise PartHtmlError
            else:
                # Look for the table of products.
                products = tree.find(
                    'table',
                    class_='SearchResultsTable').find_all(
                        'tr',
                        class_=('SearchResultsRowOdd', 'SearchResultsRowEven'))

                # Extract the product links for the part numbers from the table.
                product_links = [p.find('div', class_='mfrDiv').a for p in products]

                # Extract all the part numbers from the text portion of the links.
                part_numbers = [l.text for l in product_links]

                # Look for the part number in the list that most closely matches the requested part number.
                match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]

                # Now look for the link that goes with the closest matching part number.
                for l in product_links:
                    if l.text == match:
                        # Get the tree for the linked-to page and return that.
                        self.logger.log(DEBUG_OBSESSIVE,'Selecting {} from product table for {} from {}'.format(l.text, pn, self.name))
                        return self.dist_get_part_html_tree(pn, extra_search_terms,
                                                  url=l.get('href', ''),
                                                  descend=descend-1)

        # I don't know what happened here, so give up.
        self.logger.log(DEBUG_OBSESSIVE,'Unknown error for {} from {}'.format(pn, self.name))
        self.logger.log(DEBUG_HTTP_RESPONSES,'Response was %s' % html)
        raise PartHtmlError
