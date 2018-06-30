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
from ...global_vars import PartHtmlError
from ...global_vars import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE, DEBUG_HTTP_RESPONSES

from .. import fake_browser
from .. import distributor
from ..global_vars import distributor_dict

from urllib.parse import quote_plus as urlquote

import pycountry

class dist_mouser(distributor.distributor):
    def __init__(self, name, scrape_retries, throttle_delay):
        super(dist_mouser, self).__init__(name, distributor_dict[name]['site']['url'],
            scrape_retries, throttle_delay)
        self.browser.start_new_session()

    @staticmethod
    def dist_init_distributor_dict():
        distributor_dict.update(
        {
            'mouser': {
                'module': 'mouser',  # The directory name containing this file.
                'scrape': 'web',     # Allowable values: 'web' or 'local'.
                'label': 'Mouser',   # Distributor label used in spreadsheet columns.
                'order_cols': ['part_num', 'purch', 'refs'],  # Sort-order for online orders.
                'order_delimiter': ' ',  # Delimiter for online orders.
                # Formatting for distributor header in worksheet.
                'wrk_hdr_format': {
                    'font_size': 14,
                    'font_color': 'white',
                    'bold': True,
                    'align': 'center',
                    'valign': 'vcenter',
                    'bg_color': '#004A85'  # Mouser blue.
                },
                # Web site defitions.
                'site': {
                    'url': 'https://www.mouser.com/',
                    'currency': 'USD',
                    'locale': 'US'
                },
            }
        })

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

    def dist_define_locale_currency(self, locale_iso=None, currency_iso=None):
        '''@brief Configure the distributor for the country and currency intended.

        Scrape the configuration page and define the base URL of Mouser for the
        currency and locale chosen.
        The currency is predominant over the locale/country and the default
        settings depend on your location.

        @param locale_iso `str` Country in ISO3166 alpha 2 standard.
        @param currency_iso `str` Currency in ISO4217 alpha 3 standard.'''

        # Configuring mouser locale and currency is difficult because
        # Mouser automatically selects locale, currency and used Mouser
        # (sub)domain based on your IP address! All override attempts of
        # this behaviour within a session seems to be ignored so far
        # (you will be 302 redirected to your regional domain).

        # TODO:
        #   Switch locale via the following URL ignores currency settings!
        #   Switch to regions far away from your location is rejected!
        #   url = 'https://www.mouser.com/localsites.aspx'

        # The following approach works for selecting currency:
        # - Access "www.mouser.com" (done in constructor) and store local redirect URL.
        # - Manually set currency preference for your regional URL.
        # - Completely restart fake_browser session to apply currency settings.
        # Switching locale seems to be not possible yet.
        try:
            if currency_iso and not locale_iso:
                money = pycountry.currencies.get(alpha_3=currency_iso.upper())
                locale_iso = pycountry.countries.get(numeric=money.numeric).alpha_2
            if locale_iso:
                currency_iso = currency_iso.upper()
                country = pycountry.countries.get(alpha_2=locale_iso.upper())

                # TODO: Mouser uses either "USDe" or "USDu" to select USD as
                #   currency, depending on your location.
                if currency_iso == "USD" and locale_iso == "US":
                    currency_iso = "USDu"
                else:
                    currency_iso = "USDe"

                # Some mouser regions are subdomains from mouser.com, other
                # regions user their own top level domains, e.g. mouser.eu.
                # Extract the region specific part and suffix it to
                # the preferences cookie.
                local_domains = re.search("https://(.+)\.mouser\.(.+)/", self.browser.ret_url)
                if local_domains.group(1).startswith("www"):
                    domain = local_domains.group(2)
                else:
                    domain = local_domains.group(1)

                # Store currency perference (pc_%localdomain)
                # for your regional domain.
                self.browser.add_cookie('.mouser.%s' % local_domains.group(2), \
                    'preferences', 'pc_%s=%s' % (domain, currency_iso))

                # Store new localized url in distributor_dict.
                distributor_dict[self.name]['site']['url'] = self.browser.ret_url.rstrip('/')
                distributor_dict[self.name]['site']['currency'] = pycountry.currencies.get(numeric=country.numeric).alpha_3
                distributor_dict[self.name]['site']['locale'] = locale_iso

                # Restarting complete session is required to apply
                # new locale and currency settings.
                self.browser.domain = distributor_dict[self.name]['site']['url']
                self.browser.start_new_session()

        except Exception as ex:
            self.logger.log(DEBUG_OBSESSIVE, "Exception was %s" % type(ex).__name__)
            self.logger.log(DEBUG_OVERVIEW, 'Kept the last configuration {}, {} on {}.'.format(
                    pycountry.currencies.get(alpha_3=distributor_dict[self.name]['site']['currency']).name,
                    pycountry.countries.get(alpha_2=distributor_dict[self.name]['site']['locale']).name,
                    distributor_dict[self.name]['site']['url']
                )) # Keep the current configuration.
        return

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
            url = distributor_dict[self.name]['site']['url'] + \
                '/Search/Refine.aspx?Keyword=' + urlquote(pn, safe='')
            if extra_search_terms:
                url = url + urlquote(' ' + extra_search_terms, safe='')
        elif url[0] == '/':
            url = distributor_dict[self.name]['site']['url']  + url
        elif url.startswith('..'):
            url = distributor_dict[self.name]['site']['url']  + '/Search/' + url

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
