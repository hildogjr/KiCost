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
import difflib
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

from ..kicost import distributors
distributors.update(
    {
        'digikey': {
            'scrape': 'web',
            'function': 'digikey',
            'label': 'Digi-Key',
            'order_cols': ['purch', 'part_num', 'refs'],
            'order_delimiter': ','
        }
    }
)


def get_digikey_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Digikey product page.'''
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
        logger.log(DEBUG_OBSESSIVE, 'No Digikey pricing information found!')
        return price_tiers  # Return empty price tiers.
    return price_tiers


def digikey_part_is_reeled(html_tree):
    '''Returns True if this Digi-Key part is reeled or Digi-reeled.'''
    qty_tiers = list(get_digikey_price_tiers(html_tree).keys())
    if len(qty_tiers) > 0 and min(qty_tiers) >= 100:
        return True
    if html_tree.find('table',
                      id='product-details-reel-pricing') is not None:
        return True
    return False


def get_digikey_part_num(html_tree):
    '''Get the part number from the Digikey product page.'''
    try:
        return re.sub('\s', '', html_tree.find('td',
                                               id='reportPartNumber').text)
    except AttributeError:
        logger.log(DEBUG_OBSESSIVE, 'No Digikey part number found!')
        return ''


def get_digikey_qty_avail(html_tree):
    '''Get the available quantity of the part from the Digikey product page.'''
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
            logger.log(DEBUG_OBSESSIVE, 'No Digikey part quantity found!')
            return int(qty_tree.find('input', type='text').get('value'))
        except (AttributeError, ValueError):
            # Well, there's a quantityAvailable section in the website, but
            # it doesn't contain anything decipherable. Let's just assume it's 0.
            return 0


def get_digikey_part_html_tree(dist, pn, extra_search_terms='', url=None, descend=2, local_part_html=None):
    '''Find the Digikey HTML page for a part number and return the URL and parse tree.'''

    def merge_price_tiers(main_tree, alt_tree):
        '''Merge the price tiers from the alternate-packaging tree into the main tree.'''
        try:
            insertion_point = main_tree.find('table', id='product-dollars').find('tr')
            for tr in alt_tree.find('table', id='product-dollars').find_all('tr'):
                insertion_point.insert_after(tr)
        except AttributeError:
            logger.log(DEBUG_OBSESSIVE, 'Problem merging price tiers for Digikey part {} with alternate packaging!'.format(pn))

    def merge_qty_avail(main_tree, alt_tree):
        '''Merge the quantities from the alternate-packaging tree into the main tree.'''
        try:
            main_qty = get_digikey_qty_avail(main_tree)
            alt_qty = get_digikey_qty_avail(alt_tree)
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
            logger.log(DEBUG_OBSESSIVE, 'Problem merging available quantities for Digikey part {} with alternate packaging!'.format(pn))

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://www.digikey.com/scripts/DkSearch/dksus.dll?WT.z_header=search_go&lang=en&keywords=' + urlquote(
            pn + ' ' + extra_search_terms,
            safe='')
        #url = 'http://www.digikey.com/product-search/en?KeyWords=' + urlquote(pn,safe='') + '&WT.z_header=search_go'
    elif url[0] == '/':
        url = 'http://www.digikey.com' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    req = FakeBrowser(url)
    for _ in range(HTML_RESPONSE_RETRIES):
        try:
            response = urlopen(req)
            html = response.read()
            break
        except WEB_SCRAPE_EXCEPTIONS:
            logger.log(DEBUG_DETAILED,'Exception while web-scraping {} from {}'.format(pn, dist))

    else: # Couldn't get a good read from the website.
        logger.log(DEBUG_OBSESSIVE,'No HTML page for {} from {}'.format(pn, dist))
        raise PartHtmlError

    # Abort if the part number isn't in the HTML somewhere.
    # (Only use the numbers and letters to compare PN to HTML.)
    if re.sub('[\W_]','',str.lower(pn)) not in re.sub('[\W_]','',str.lower(str(html))):
        logger.log(DEBUG_OBSESSIVE,'No part number {} in HTML page from {}'.format(pn, dist))
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
        logger.log(DEBUG_OBSESSIVE,'No HTML tree for {} from {}'.format(pn, dist))
        raise PartHtmlError

    # If the tree contains the tag for a product page, then return it.
    if tree.find('div', class_='product-top-section') is not None:

        # Digikey separates cut-tape and reel packaging, so we need to examine more pages
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
                logger.log(DEBUG_OBSESSIVE,'Found {} alternate packagings for {} from {}'.format(len(ap_urls), pn, dist))
                ap_trees_and_urls = []  # Initialize as empty in case no alternate packagings are found.
                try:
                    ap_trees_and_urls = [get_digikey_part_html_tree(dist, pn, 
                                     extra_search_terms, ap_url, descend=0)
                                     for ap_url in ap_urls]
                except Exception:
                    logger.log(DEBUG_OBSESSIVE,'Failed to find alternate packagings for {} from {}'.format(pn, dist))

                # Put the main tree on the list as well and then look through
                # the entire list for one that's non-reeled. Use this as the
                # main page for the part.
                ap_trees_and_urls.append((tree, url))
                if digikey_part_is_reeled(tree):
                    for ap_tree, ap_url in ap_trees_and_urls:
                        if not digikey_part_is_reeled(ap_tree):
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
                        merge_price_tiers(tree, ap_tree)
                        # and merge available quantity, using the maximum found.
                        merge_qty_avail(tree, ap_tree)
                    except AttributeError:
                        logger.log(DEBUG_OBSESSIVE,'Problem merging price/qty for {} from {}'.format(pn, dist))
                        continue
            except AttributeError as e:
                logger.log(DEBUG_OBSESSIVE,'Problem parsing URLs from product page for {} from {}'.format(pn, dist))

        return tree, url  # Return the parse tree and the URL where it came from.

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('table', id='productTable') is not None:
        logger.log(DEBUG_OBSESSIVE,'Found product table for {} from {}'.format(pn, dist))
        if descend <= 0:
            logger.log(DEBUG_OBSESSIVE,'Passed descent limit for {} from {}'.format(pn, dist))
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
                    logger.log(DEBUG_OBSESSIVE,'Selecting {} from product table for {} from {}'.format(l.text, pn, dist))
                    return get_digikey_part_html_tree(dist, pn, extra_search_terms,
                                                      url=l['href'],
                                                      descend=descend - 1)

    # If the HTML contains a list of part categories, then give up.
    if tree.find('form', id='keywordSearchForm') is not None:
        logger.log(DEBUG_OBSESSIVE,'Found high-level part categories for {} from {}'.format(pn, dist))
        raise PartHtmlError

    # I don't know what happened here, so give up.
    logger.log(DEBUG_OBSESSIVE,'Unknown error for {} from {}'.format(pn, dist))
    raise PartHtmlError
