# MIT license
#
# Copyright (C) 2015 by XESS Corporation / Hildo Guillardi Junior / Max Maisel
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
from ..global_vars import distributor_dict, EXTRA_INFO_DIST, extra_info_dist_name_translations

from urllib.parse import quote_plus as urlquote

import pycountry

class dist_digikey(distributor.distributor):
    def __init__(self, name, scrape_retries, throttle_delay):
        super(dist_digikey, self).__init__(name, distributor_dict[name]['site']['url'],
            scrape_retries, throttle_delay)
        self.browser.start_new_session()

    @staticmethod
    def dist_init_distributor_dict():
        distributor_dict.update(
        {
            'digikey': {
                'module': 'digikey', # The directory name containing this file.
                'scrape': 'web',     # Allowable values: 'web' or 'local'.
                'label': 'Digi-Key', # Distributor label used in spreadsheet columns.
                'order_cols': ['purch', 'part_num', 'refs'],  # Sort-order for online orders.
                'order_delimiter': ',',  # Delimiter for online orders.
                # Formatting for distributor header in worksheet.
                'wrk_hdr_format': {
                    'font_size': 14,
                    'font_color': 'white',
                    'bold': True,
                    'align': 'center',
                    'valign': 'vcenter',
                    'bg_color': '#CC0000'  # Digi-Key red.
                },
                # Web site defitions.
                'site': {
                    'url': 'https://www.digikey.com',
                    'currency': 'USD',
                    'locale': 'US'
                },
            }
        })

    def dist_get_price_tiers(self, html_tree):
        '''@brief Get the pricing tiers from the parsed tree of the Digikey product page.
           @param html_tree `str()` html of the distributor part page.
           @return `dict()` price breaks, the keys are the quantities breaks.
        '''
        price_tiers = {}
        try:
            for tr in html_tree.find('table', id='product-dollars').find_all('tr'):
                try:
                    td = tr.find_all('td')
                    qty = int(re.sub('[^0-9]', '', td[0].text))
                    price_tiers[qty] = float(re.sub('[^0-9\.]', '', td[1].text))
                except (TypeError, AttributeError, ValueError,
                        IndexError):  # Happens when there's no <td> in table row.
                    continue
        except AttributeError:
            # This happens when no pricing info is found in the tree.
            self.logger.log(DEBUG_OBSESSIVE, 'No Digikey pricing information found!')
        return price_tiers

    def dist_get_extra_info(self, html_tree):
        '''@brief Get the extra characteristics `EXTRA_INFO_DIST` from the part web page.
           @param html_tree `str()` html of the distributor part page.
           @return `dict()` keys as characteristics names.
        '''
        info = {}
        try:
            table =  html_tree.find('table', id='prod-att-table')
            for row in table.find_all('tr', id=None): # `None`to ignore the header row.
                try:
                    k = row.find('th').text.strip().lower()
                    v = row.find('td').text.strip()
                    k = extra_info_dist_name_translations.get(k, k)
                    if k in EXTRA_INFO_DIST:
                        info[k] = v
                except:
                    continue
            if 'datasheet' in EXTRA_INFO_DIST:
                try:
                    info['datasheet'] = html_tree.find('a', href=True, target='_blank').get('href')
                    if info['datasheet'][0:2]=='//':
                        info['datasheet'] = 'https:' + info['datasheet'] # Digikey missing definitions.
                except:
                    pass
            if 'image' in EXTRA_INFO_DIST:
                try:
                    info['image'] = html_tree.find('img', itemprop="image").get('src')
                    if info['image'][0:2]=='//':
                        info['image'] = 'https:' + info['image'] # Digikey missing definitions.
                except:
                    pass
        except AttributeError:
            # This happens when no pricing info is found in the tree.
            self.logger.log(DEBUG_OBSESSIVE, 'No Digikey pricing information found!')
        return info

    def dist_define_locale_currency(self, locale_iso=None, currency_iso=None):
        '''@brief Configure the distributor for the country and currency intended.
        
        Scrape the configuration page and define the base URL of DigiKey for the
        currency and locale chosen.
        The currency is predominant over the locale/country and the defauld are
        currency='USD' and locale='US' for DigiKey.
        
        @param locale_iso `str` Country in ISO3166 alpha 2 standard.
        @param currency_iso `str` Currency in ISO4217 alpha 3 standard.'''

        url = 'https://www.digikey.com/en/resources/international'

        try:
            html = self.browser.scrape_URL(url)
        except: # Could not get a good read from the website.
            self.logger.log(DEBUG_OBSESSIVE,'No HTML page for DigiKey configuration.')
            raise PartHtmlError
        html = BeautifulSoup(html, 'lxml')
        try:
            if currency_iso and not locale_iso:
                money = pycountry.currencies.get(alpha_3=currency_iso.upper())
                locale_iso = pycountry.countries.get(numeric=money.numeric).alpha_2
            if locale_iso:
                locale_iso = locale_iso.upper()
                country = pycountry.countries.get(alpha_2=locale_iso.upper())
                html = html.find('li', text=re.compile(country.name, re.IGNORECASE))
                url = html.find('a', id='linkcolor').get('href')

                # Store new localized url in distributor_dict.
                distributor_dict[self.name]['site']['url'] = url
                distributor_dict[self.name]['site']['currency'] = pycountry.currencies.get(numeric=country.numeric).alpha_3
                distributor_dict[self.name]['site']['locale'] = locale_iso

                # Fetch cookies for new URL.
                self.browser.scrape_URL(url)
        except:
            self.logger.log(DEBUG_OVERVIEW, 'Kept the last configuration {}, {} on {}.'.format(
                    pycountry.currencies.get(alpha_3=distributor_dict['digikey']['site']['currency']).name,
                    pycountry.countries.get(alpha_2=distributor_dict['digikey']['site']['locale']).name,
                    distributor_dict[self.name]['site']['url']
                )) # Keep the current configuration.
        return

    def dist_get_part_num(self, html_tree):
        '''@brief Get the part number from the Digikey product page.
           @param html_tree `str()` html of the distributor part page.
           @return `list()`of the parts that match.
        '''
        try:
            return re.sub('\s', '', html_tree.find('td',
                                                   id='reportPartNumber').text)
        except AttributeError:
            self.logger.log(DEBUG_OBSESSIVE, 'No Digikey part number found!')
            return ''


    def dist_get_qty_avail(self, html_tree):
        '''@brief Get the available quantity of the part from the Digikey product page.
           @param html_tree `str()` html of the distributor part page.
           @return `int` avaliable quantity.
        '''
        try:
            qty_tree = html_tree.find('td', id='quantityAvailable').find('span', id='dkQty')
            qty_str = qty_tree.text
        except AttributeError:
            # No quantity found (not even 0) so this is probably a non-stocked part.
            # Return None so the part won't show in the spreadsheet for this dist.
            return None
        try:
            qty_str = re.search('([0-9,]*)', qty_str, re.IGNORECASE).group(1)
            return int(re.sub('[^0-9]', '', qty_str))
        except (AttributeError, ValueError):
            # Didn't find the usual quantity text field. This might be one of those
            # input fields for requesting a quantity, so get the value from the
            # input field.
            try:
                self.logger.log(DEBUG_OBSESSIVE, 'No Digikey part quantity found!')
                return int(qty_tree.find('input', type='text').get('value'))
            except (AttributeError, ValueError):
                # Well, there's a quantityAvailable section in the website, but
                # it doesn't contain anything decipherable. Let's just assume it's 0.
                return 0

    def dist_get_part_html_tree(self, pn, extra_search_terms='', url=None, descend=2):
        '''@brief Find the Digikey HTML page for a part number and return the URL and parse tree.
           @param pn Part number `str()`.
           @param extra_search_terms
           @param url
           @param descend
           @return (html `str()` of the page, url)
        '''

        # Use the part number to lookup the part using the site search function, unless a starting url was given.
        if url is None:
            url = distributor_dict['digikey']['site']['url'] + '/products/en?keywords=' + urlquote(pn, safe='')
            if extra_search_terms:
                url = url + urlquote(' ' + extra_search_terms, safe='')
        elif url[0] == '/':
            url = distributor_dict['digikey']['site']['url'] + url

        # Open the URL, read the HTML from it, and parse it into a tree structure.
        try:
            html = self.browser.scrape_URL(url)
        except Exception as ex:
            self.logger.log(DEBUG_OBSESSIVE,'No HTML page for {} from {}, ex: {}'.format(pn, self.name, type(ex).__name__))
            raise PartHtmlError

        # Abort if the part number isn't in the HTML somewhere.
        # (Only use the numbers and letters to compare PN to HTML.)
        if re.sub('[\W_]','',str.lower(pn)) not in re.sub('[\W_]','',str.lower(str(html))):
            self.logger.log(DEBUG_OBSESSIVE,'No part number {} in HTML page from {}'.format(pn, self.name))
            raise PartHtmlError

        # Use the following code if Javascript challenge pages are used to block scrapers.
        # try:
        # ghst = Ghost()
        # sess = ghst.start(plugins_enabled=False, download_images=False, show_scrollbars=False, javascript_enabled=False)
        # html, resources = sess.open(url)
        # print('type of HTML is {}'.format(type(html.content)))
        # html = html.content
        # except Exception as e:
        # print('Exception reading with Ghost: {}'.format(e))

        try:
            tree = BeautifulSoup(html, 'lxml')
        except Exception:
            self.logger.log(DEBUG_OBSESSIVE,'No HTML tree for {} from {}'.format(pn, self.name))
            raise PartHtmlError

        # If the tree contains the tag for a product page, then return it.
        if tree.find('div', class_='product-top-section') is not None:

            # Digikey separprint(ates cut-tape and reel packaging, so we need to examine more pages
            # to get all the pricing info. But don't descend any further if limit has been reached.
            if descend > 0:
                try:
                    # Find all the URLs to alternate-packaging pages for this part.
                    ap_urls = [
                        ap.find('li', class_='lnkAltPack').find_all('a')[-1].get('href')
                        for ap in tree.find(
                            'div', class_='bota',
                            id='additionalPackaging').find_all(
                                'ul', class_='more-expander-item')
                    ]
                    self.logger.log(DEBUG_OBSESSIVE,'Found {} alternate packagings for {} from {}'.format(len(ap_urls), pn, self.name))
                    ap_trees_and_urls = []  # Initialize as empty in case no alternate packagings are found.
                    try:
                        ap_trees_and_urls = [self.dist_get_part_html_tree(pn, 
                                         extra_search_terms, ap_url, descend=0)
                                         for ap_url in ap_urls]
                    except Exception:
                        self.logger.log(DEBUG_OBSESSIVE,'Failed to find alternate packagings for {} from {}'.format(pn, self.name))

                    # Put the main tree on the list as well and then look through
                    # the entire list for one that's non-reeled. Use this as the
                    # main page for the part.
                    ap_trees_and_urls.append((tree, url))
                    if self.part_is_reeled(tree):
                        for ap_tree, ap_url in ap_trees_and_urls:
                            if not self.part_is_reeled(ap_tree):
                                # Found a non-reeled part, so use it as the main page.
                                tree = ap_tree
                                url = ap_url
                                break  # Done looking.

                    # Now go through the other pages, merging their pricing and quantity
                    # info into the main page.
                    for ap_tree, ap_url in ap_trees_and_urls:
                        if ap_tree is tree:
                            continue  # Skip examining the main tree. It already contains its info.
                        try:
                            # Merge the pricing info from that into the main parse tree to make
                            # a single, unified set of price tiers...
                            self.merge_price_tiers(tree, ap_tree)
                            # and merge available quantity, using the maximum found.
                            self.merge_qty_avail(tree, ap_tree)
                        except AttributeError:
                            self.logger.log(DEBUG_OBSESSIVE,'Problem merging price/qty for {} from {}'.format(pn, self.name))
                            continue
                except AttributeError as e:
                    self.logger.log(DEBUG_OBSESSIVE,'Problem parsing URLs from product page for {} from {}'.format(pn, self.name))

            return tree, url  # Return the parse tree and the URL where it came from.

        # If the tree is for a list of products, then examine the links to try to find the part number.
        if tree.find('table', id='productTable') is not None:
            self.logger.log(DEBUG_OBSESSIVE,'Found product table for {} from {}'.format(pn, self.name))
            if descend <= 0:
                self.logger.log(DEBUG_OBSESSIVE,'Passed descent limit for {} from {}'.format(pn, self.name))
                raise PartHtmlError
            else:
                # Look for the table of products.
                products = tree.find(
                    'table',
                    id='productTable').find('tbody').find_all('tr')

                # Extract the product links for the part numbers from the table.
                # Extract links for both manufacturer and catalog numbers.
                product_links = [p.find('td',
                                        class_='tr-mfgPartNumber').a
                                 for p in products]
                product_links.extend([p.find('td',
                                        class_='tr-dkPartNumber').a
                                 for p in products])

                # Extract all the part numbers from the text portion of the links.
                part_numbers = [l.text for l in product_links]

                # Look for the part number in the list that most closely matches the requested part number.
                match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]

                # Now look for the link that goes with the closest matching part number.
                for l in product_links:
                    if l.text == match:
                        # Get the tree for the linked-to page and return that.
                        self.logger.log(DEBUG_OBSESSIVE,'Selecting {} from product table for {} from {}'.format(l.text.strip(), pn, self.name))
                        return self.dist_get_part_html_tree(pn, extra_search_terms,
                                                  url=l.get('href', ''),
                                                  descend=descend - 1)

        # If the HTML contains a list of part categories, then give up.
        if tree.find('form', id='keywordSearchForm') is not None:
            self.logger.log(DEBUG_OBSESSIVE,'Found high-level part categories for {} from {}'.format(pn, self.name))
            raise PartHtmlError

        # I don't know what happened here, so give up.
        self.logger.log(DEBUG_OBSESSIVE,'Unknown error for {} from {}'.format(pn, self.name))
        self.logger.log(DEBUG_HTTP_RESPONSES,'Response was %s' % html)
        raise PartHtmlError

    def part_is_reeled(self, html_tree):
        '''@brief Returns True if this Digi-Key part is reeled or Digi-reeled.
           @param html_tree `str()` html of the distributor part page.
           @return `True` or `False`.
        '''
        qty_tiers = list(self.dist_get_price_tiers(html_tree).keys())
        if len(qty_tiers) > 0 and min(qty_tiers) >= 100:
            return True
        if html_tree.find('table',
                          id='product-details-reel-pricing') is not None:
            return True
        return False

    def merge_price_tiers(self, main_tree, alt_tree):
        '''Merge the price tiers from the alternate-packaging tree into the main tree.'''
        try:
            insertion_point = main_tree.find('table', id='product-dollars').find('tr')
            for tr in alt_tree.find('table', id='product-dollars').find_all('tr'):
                insertion_point.insert_after(tr)
        except AttributeError:
            self.logger.log(DEBUG_OBSESSIVE, 'Problem merging price tiers for Digikey part {} with alternate packaging!'.format(pn))

    def merge_qty_avail(self, main_tree, alt_tree):
        '''Merge the quantities from the alternate-packaging tree into the main tree.'''
        try:
            main_qty = self.dist_get_qty_avail(main_tree)
            alt_qty = self.dist_get_qty_avail(alt_tree)
            if main_qty is None:
                merged_qty = alt_qty
            elif alt_qty is None:
                merged_qty = main_qty
            else:
                merged_qty = max(main_qty, alt_qty)
            if merged_qty is not None:
                insertion_point = main_tree.find('td', id='quantityAvailable').find('span', id='dkQty')
                insertion_point.string = '{}'.format(merged_qty)
        except AttributeError:
            self.logger.log(DEBUG_OBSESSIVE, 'Problem merging available quantities for Digikey part {} with alternate packaging!'.format(pn))


