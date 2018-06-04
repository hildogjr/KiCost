# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Junior
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

class dist_newark(distributor.distributor):
    def __init__(self, name, scrape_retries, log_level, throttle_delay):
        super(dist_newark, self).__init__(name, scrape_retries, log_level, throttle_delay)
        self.domain = distributor_dict[self.name]['site']['url']

        self.browser.scrape_URL(self.domain)
        self.browser.show_cookies(self.name)

    def dist_get_price_tiers(self, html_tree):
        '''@brief Get the pricing tiers from the parsed tree of the Newark product page.
           @param html_tree `str()` html of the distributor part page.
           @return `dict()` price breaks, the keys are the quantities breaks.
        '''
        price_tiers = {}
        try:
            qty_strs = []
            for qty in html_tree.find(
                'table',
                class_=('tableProductDetailPrice', 'pricing')).find_all(
                    'td',
                    class_='qty'):
                qty_strs.append(qty.text)
            price_strs = []
            for price in html_tree.find(
                'table',
                class_=('tableProductDetailPrice', 'pricing')).find_all(
                    'td',
                    class_='threeColTd'):
                price_strs.append(price.text)
            qtys_prices = list(zip(qty_strs, price_strs))
            for qty_str, price_str in qtys_prices:
                try:
                    qty = re.search('(\s*)([0-9,]+)', qty_str).group(2)
                    qty = int(re.sub('[^0-9]', '', qty))
                    price_tiers[qty] = float(re.sub('[^0-9\.]', '', price_str))
                except (TypeError, AttributeError, ValueError):
                    continue
        except AttributeError:
            # This happens when no pricing info is found in the tree.
            self.logger.log(DEBUG_OBSESSIVE, 'No Newark pricing information found!')
            return price_tiers  # Return empty price tiers.
        return price_tiers


    def dist_get_part_num(self, html_tree):
        '''@brief Get the part number from the Newark product page.
           @param html_tree `str()` html of the distributor part page.
           @return `list()`of the parts that match.
        '''
        try:
            # Newark catalog number is stored in a description list, so get
            # all the list terms and descriptions, strip all the spaces from those,
            # and pair them up.
            div = html_tree.find('div', class_='productDescription').find('dl')
            dt = [re.sub('\s','',d.text) for d in div.find_all('dt')]
            dd = [re.sub('\s','',d.text) for d in div.find_all('dd')]
            dtdd = {k:v for k,v in zip(dt,dd)}  # Pair terms with descriptions.
            return dtdd.get('NewarkPartNo.:', '')
        except KeyError:
            self.logger.log(DEBUG_OBSESSIVE, 'No Newark catalog number found!')
            return '' # No catalog number found in page.
        except AttributeError:
            self.logger.log(DEBUG_OBSESSIVE, 'No Newark product description found!')
            return '' # No ProductDescription found in page.


    def dist_get_qty_avail(self, html_tree):
        '''@brief Get the available quantity of the part from the Newark product page.
           @param html_tree `str()` html of the distributor part page.
           @return `int` avaliable quantity.
        '''
        try:
            qty_str = html_tree.find('p', class_='availabilityHeading').text
        except (AttributeError, ValueError):
            # No quantity found (not even 0) so this is probably a non-stocked part.
            # Return None so the part won't show in the spreadsheet for this dist.
            return None
        try:
            qty = re.sub('[^0-9]','',qty_str)  # Strip all non-number chars.
            return int(re.sub('[^0-9]', '', qty_str))  # Return integer for quantity.
        except ValueError:
            # No quantity found (not even 0) so this is probably a non-stocked part.
            # Return None so the part won't show in the spreadsheet for this dist.
            self.logger.log(DEBUG_OBSESSIVE, 'No Newark part quantity found!')
            return None


    def dist_get_part_html_tree(self, pn, extra_search_terms='', url=None, descend=2):
        '''@brief Find the Newark HTML page for a part number and return the URL and parse tree.
           @param pn Part number `str()`.
           @param extra_search_terms
           @param url
           @param descend
           @return (html `str()` of the page, url)
        '''

        # Use the part number to lookup the part using the site search function, unless a starting url was given.
        if url is None:
            url = 'http://www.newark.com/webapp/wcs/stores/servlet/Search?catalogId=15003&langId=-1&storeId=10194&gs=true&st=' + urlquote(
                pn + ' ' + extra_search_terms,
                safe='')
        elif url[0] == '/':
            url = 'http://www.newark.com' + url
        elif url.startswith('..'):
            url = 'http://www.newark.com/Search/' + url

        # Open the URL, read the HTML from it, and parse it into a tree structure.
        try:
            html = self.browser.scrape_URL(url)
        except:
            self.logger.log(DEBUG_OBSESSIVE,'No HTML page for {} from {}'.format(pn, self.name))
            raise PartHtmlError

        try:
            tree = BeautifulSoup(html, 'lxml')
        except Exception:
            self.logger.log(DEBUG_OBSESSIVE,'No HTML tree for {} from {}'.format(pn, self.name))
            raise PartHtmlError

        # Abort if the part number isn't in the HTML somewhere.
        # (Only use the numbers and letters to compare PN to HTML.)
        if re.sub('[\W_]','',str.lower(pn)) not in re.sub('[\W_]','',str.lower(str(html))):
            self.logger.log(DEBUG_OBSESSIVE,'No part number {} in HTML page from {}'.format(pn, self.name))
            raise PartHtmlError

        # If the tree contains the tag for a product page, then just return it.
        if tree.find('div', class_='productDisplay', id='page') is not None:
            return tree, url

        # If the tree is for a list of products, then examine the links to try to find the part number.
        if tree.find('table', class_='productLister', id='sProdList') is not None:
            self.logger.log(DEBUG_OBSESSIVE,'Found product table for {} from {}'.format(pn, self.name))
            if descend <= 0:
                self.logger.log(DEBUG_OBSESSIVE,'Passed descent limit for {} from {}'.format(pn, self.name))
                raise PartHtmlError
            else:
                # Look for the table of products.
                products = tree.find('table',
                                     class_='productLister',
                                     id='sProdList').find('tbody').find_all('tr')

                # Extract the product links for the part numbers from the table.
                product_links = []
                for p in products:
                    try:
                        product_links.append(
                            p.find('td', class_='mftrPart').find('a'))
                    except AttributeError:
                        continue

                # Extract all the part numbers from the text portion of the links.
                part_numbers = [l.text for l in product_links]

                # Look for the part number in the list that most closely matches the requested part number.
                try:
                    match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]
                except IndexError:
                    raise PartHtmlError

                # Now look for the link that goes with the closest matching part number.
                for l in product_links:
                    if l.text == match:
                        # Get the tree for the linked-to page and return that.
                        self.logger.log(DEBUG_OBSESSIVE,'Selecting {} from product table for {} from {}'.format(l.text.strip(), pn, self.name))
                        return self.dist_get_part_html_tree(pn, extra_search_terms,
                                    url=l.get('href', ''),
                                    descend=descend-1)

        # I don't know what happened here, so give up.
        self.logger.log(DEBUG_OBSESSIVE,'Unknown error for {} from {}'.format(pn, self.name))
        self.logger.log(DEBUG_HTTP_RESPONSES,'Response was %s' % html)
        raise PartHtmlError
