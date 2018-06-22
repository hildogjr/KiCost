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
from __future__ import print_function, unicode_literals, division, absolute_import
from builtins import zip, range, int, str
from future import standard_library
standard_library.install_aliases()
import future

import re, difflib
import json
from bs4 import BeautifulSoup
import http.client # For web scraping exceptions.
from .. import fake_browser
from ...global_vars import PartHtmlError
from ...global_vars import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE, DEBUG_HTTP_RESPONSES

from .. import distributor
from ..global_vars import distributor_dict

from urllib.parse import quote_plus as urlquote

class dist_tme(distributor.distributor):
    def __init__(self, name, scrape_retries, throttle_delay):
        super(dist_tme, self).__init__(name, distributor_dict[name]['site']['url'],
            scrape_retries, throttle_delay)
        self.browser.start_new_session()

    @staticmethod
    def dist_init_distributor_dict():
        distributor_dict.update(
        {
            'tme': {
                'module': 'tme', # The directory name containing this file.
                'scrape': 'web',     # Allowable values: 'web' or 'local'.
                'label': 'TME',  # Distributor label used in spreadsheet columns.
                'order_cols': ['part_num', 'purch', 'refs'],  # Sort-order for online orders.
                'order_delimiter': ' ',  # Delimiter for online orders.
                # Formatting for distributor header in worksheet.
                'wrk_hdr_format': {
                    'font_size': 14,
                    'font_color': 'white',
                    'bold': True,
                    'align': 'center',
                    'valign': 'vcenter',
                    'bg_color': '#0C4DA1'  # TME blue
                },
                # Web site defitions.
                'site': {
                'url': 'https://www.tme.eu/en/',
                'currency': 'USD',
                'locale': 'UK'
                },
            }
        })

    def __ajax_details(self, pn):
        '''@brief Load part details from TME using XMLHttpRequest.
           @param pn `str()` part number
           @return (html, quantity avaliable)
        '''
        data = { 'symbol': pn, 'currency': 'USD'}
        try:
            html = self.browser.ajax_request('https://www.tme.eu/en/_ajax/ProductInformationPage/_getStocks.html', data)
        except: # Couldn't get a good read from the website.
            self.logger.log(DEBUG_OBSESSIVE,'No AJAX data for {} from {}'.format(pn, 'TME'))
            return None, None

        try:
            p = json.loads(html).get('Products')
            if p is not None and isinstance(p, list):
                p = p[0]
                html_tree = BeautifulSoup(p.get('PriceTpl', '').replace("\n", ""), "lxml")
                quantity = p.get('InStock', '0')
                return html_tree, quantity
            else:
                return None, None
        except (ValueError, KeyError, IndexError):
            self.logger.log(DEBUG_OBSESSIVE, 'Could not obtain AJAX data from TME!')
            return None, None

    def dist_get_price_tiers(self, html_tree):
        '''@brief Get the pricing tiers from the parsed tree of the TME product page.
           @param html_tree `str()` html of the distributor part page.
           @return `dict()` price breaks, the keys are the quantities breaks.
        '''
        price_tiers = {}
        try:
            pn = self.dist_get_part_num(html_tree)
            if pn == '':
                return price_tiers

            ajax_tree, quantity = self.__ajax_details(pn)
            if ajax_tree is None:
                return price_tiers

            qty_strs = []
            price_strs = []
            for tr in ajax_tree.find('tbody', id='prices_body').find_all('tr'):
                td = tr.find_all('td')
                if len(td) == 3:
                    qty_strs.append(td[0].text)
                    price_strs.append(td[2].text)

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
            self.logger.log(DEBUG_OBSESSIVE, 'No TME pricing information found!')
            return price_tiers  # Return empty price tiers.
        return price_tiers


    def dist_get_part_num(self, html_tree):
        '''@brief Get the part number from the TME product page.
           @param html_tree `str()` html of the distributor part page.
           @return `list()`of the parts that match.
        '''
        try:
            return html_tree.find('td', class_="pip-product-symbol").text
        except AttributeError:
            self.logger.log(DEBUG_OBSESSIVE, 'No TME part number found!')
            return ''


    def dist_get_qty_avail(self, html_tree):
        '''@brief Get the available quantity of the part from the TME product page.
           @param html_tree `str()` html of the distributor part page.
           @return `int` avaliable quantity.
        '''
        pn = self.dist_get_part_num(html_tree)
        if pn == '':
            self.logger.log(DEBUG_OBSESSIVE, 'No TME part quantity found!')
            return None

        ajax_tree, qty_str = self.__ajax_details(pn)
        if qty_str is None:
            return None

        try:
            return int(qty_str)
        except ValueError:
            # No quantity found (not even 0) so this is probably a non-stocked part.
            # Return None so the part won't show in the spreadsheet for this dist.
            self.logger.log(DEBUG_OBSESSIVE, 'No TME part quantity found!')
            return None


    def dist_get_part_html_tree(self, pn, extra_search_terms='', url=None, descend=2):
        '''@brief Find the TME HTML page for a part number and return the URL and parse tree.
           @param pn Part number `str()`.
           @param extra_search_terms
           @param url
           @param descend
           @return (html `str()` of the page, url)
        '''

        # Use the part number to lookup the part using the site search function, unless a starting url was given.
        if url is None:
            url = 'https://www.tme.eu/en/katalog/?search=' + urlquote(pn, safe='')
            if extra_search_terms:
                url = url + urlquote(' ' + extra_search_terms, safe='')
        elif url[0] == '/':
            url = 'https://www.tme.eu' + url

        # Open the URL, read the HTML from it, and parse it into a tree structure.
        try:
            html = self.browser.scrape_URL(url)
        except:
            self.logger.log(DEBUG_OBSESSIVE,'No HTML page for {} from {}'.format(pn, self.name))
            raise PartHtmlError

        # Abort if the part number isn't in the HTML somewhere.
        # (Only use the numbers and letters to compare PN to HTML.)
        if re.sub('[\W_]','',str.lower(pn)) not in re.sub('[\W_]','',str.lower(str(html))):
            self.logger.log(DEBUG_OBSESSIVE,'No part number {} in HTML page from {} ({})'.format(pn, self.name, url))
            raise PartHtmlError

        try:
            tree = BeautifulSoup(html, 'lxml')
        except Exception:
            self.logger.log(DEBUG_OBSESSIVE,'No HTML tree for {} from {}'.format(pn, self.name))
            raise PartHtmlError

        # If the tree contains the tag for a product page, then just return it.
        if tree.find('div', id='ph') is not None:
            return tree, url

        # If the tree is for a list of products, then examine the links to try to find the part number.
        if tree.find('table', id="products") is not None:
            self.logger.log(DEBUG_OBSESSIVE,'Found product table for {} from {}'.format(pn, self.name))
            if descend <= 0:
                self.logger.log(DEBUG_OBSESSIVE,'Passed descent limit for {} from {}'.format(pn, self.name))
                raise PartHtmlError
            else:
                # Look for the table of products.
                products = tree.find(
                    'table',
                    id="products").find_all(
                        'tr',
                        class_=('product-row'))

                # Extract the product links for the part numbers from the table.
                product_links = []
                for p in products:
                    for a in p.find('td', class_='product').find_all('a'):
                        product_links.append(a)

                # Extract all the part numbers from the text portion of the links.
                part_numbers = [l.text for l in product_links]

                # Look for the part number in the list that most closely matches the requested part number.
                match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]

                # Now look for the link that goes with the closest matching part number.
                for l in product_links:
                    try:
                        if (not l.get('href', '').startswith('./katalog')) and l.text == match:
                            # Get the tree for the linked-to page and return that.
                            self.logger.log(DEBUG_OBSESSIVE,'Selecting {} from product table for {} from {}'.format(l.text, pn, self.name))
                            # TODO: The current implementation does up to four HTTP
                            # requests per part (search, part details page for TME P/N,
                            # XHR for pricing information, and XHR for stock
                            # availability). This is mainly for the compatibility with
                            # other distributor implementations (html_tree gets passed
                            # to all functions).
                            # A modified implementation (which would pass JSON data
                            # obtained by the XHR instead of the HTML DOM tree) might be
                            # able to do the same with just two requests (search for TME
                            # P/N, XHR for pricing and stock availability).
                            return self.dist_get_part_html_tree(pn, extra_search_terms,
                                                      url=l.get('href', ''),
                                                      descend=descend-1)
                    except KeyError:
                        pass    # This happens if there is no 'href' in the link, so just skip it.

        # I don't know what happened here, so give up.
        self.logger.log(DEBUG_OBSESSIVE,'Unknown error for {} from {}'.format(pn, self.name))
        self.logger.log(DEBUG_HTTP_RESPONSES,'Response was %s' % html)
        raise PartHtmlError
