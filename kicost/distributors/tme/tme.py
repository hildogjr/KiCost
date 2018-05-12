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
import json
from bs4 import BeautifulSoup
import http.client # For web scraping exceptions.
from .. import urlencode, urlquote, urlsplit, urlunsplit
from .. import fake_browser
from ...globals import PartHtmlError
from ...globals import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE

HTML_RESPONSE_RETRIES = 2

def __ajax_details(pn):
    '''@brief Load part details from TME using XMLHttpRequest.
       @param pn `str()` part number
       @return (html, quantity avaliable)
    '''
    data = urlencode({
        'symbol': pn,
        'currency': 'USD'
    }).encode("utf-8")
    
    try:
        html = fake_browser('https://www.tme.eu/en/_ajax/ProductInformationPage/_getStocks.html', 4, ('X-Requested-With', 'XMLHttpRequest') )
    except: # Couldn't get a good read from the website.
        logger.log(DEBUG_OBSESSIVE,'No AJAX data for {} from {}'.format(pn, 'TME'))
        return None, None

    try:
        r = r.decode('utf-8')  # Convert bytes to string in Python 3.
        p = json.loads(r).get('Products')
        if p is not None and isinstance(p, list):
            p = p[0]
            html_tree = BeautifulSoup(p.get('PriceTpl', '').replace("\n", ""), "lxml")
            quantity = p.get('InStock', '0')
            return html_tree, quantity
        else:
            return None, None
    except (ValueError, KeyError, IndexError):
        logger.log(DEBUG_OBSESSIVE, 'Could not obtain AJAX data from TME!')
        return None, None

def get_price_tiers(html_tree):
    '''@brief Get the pricing tiers from the parsed tree of the TME product page.
       @param html_tree `str()` html of the distributor part page.
       @return `dict()` price breaks, the keys are the quantities breaks.
    '''
    price_tiers = {}
    try:
        pn = get_part_num(html_tree)
        if pn == '':
            return price_tiers

        ajax_tree, quantity = __ajax_details(pn)
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
        logger.log(DEBUG_OBSESSIVE, 'No TME pricing information found!')
        return price_tiers  # Return empty price tiers.
    return price_tiers


def get_part_num(html_tree):
    '''@brief Get the part number from the TME product page.
       @param html_tree `str()` html of the distributor part page.
       @return `list()`of the parts that match.
    '''
    try:
        return html_tree.find('td', class_="pip-product-symbol").text
    except AttributeError:
        logger.log(DEBUG_OBSESSIVE, 'No TME part number found!')
        return ''


def get_qty_avail(html_tree):
    '''@brief Get the available quantity of the part from the TME product page.
       @param html_tree `str()` html of the distributor part page.
       @return `int` avaliable quantity.
    '''
    pn = get_part_num(html_tree)
    if pn == '':
        logger.log(DEBUG_OBSESSIVE, 'No TME part quantity found!')
        return None

    ajax_tree, qty_str = __ajax_details(pn)
    if qty_str is None:
        return None

    try:
        return int(qty_str)
    except ValueError:
        # No quantity found (not even 0) so this is probably a non-stocked part.
        # Return None so the part won't show in the spreadsheet for this dist.
        logger.log(DEBUG_OBSESSIVE, 'No TME part quantity found!')
        return None


def get_part_html_tree(dist, pn, extra_search_terms='', url=None, descend=2, local_part_html=None, scrape_retries=2):
    '''@brief Find the TME HTML page for a part number and return the URL and parse tree.
       @param dist
       @param pn Part number `str()`.
       @param extra_search_terms
       @param url
       @param descend
       @param local_part_html
       @param scrape_retries `int` Quantity of retries in case of fail.
       @return (html `str()` of the page, url)
    '''

    global HTML_RESPONSE_RETRIES
    HTML_RESPONSE_RETRIES = scrape_retries

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'https://www.tme.eu/en/katalog/?search=' + urlquote(
            pn + ' ' + extra_search_terms,
            safe='')
    elif url[0] == '/':
        url = 'https://www.tme.eu' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    try:
        html = fake_browser(url, scrape_retries)
    except:
        logger.log(DEBUG_OBSESSIVE,'No HTML page for {} from {}'.format(pn, dist))
        raise PartHtmlError

    # Abort if the part number isn't in the HTML somewhere.
    # (Only use the numbers and letters to compare PN to HTML.)
    if re.sub('[\W_]','',str.lower(pn)) not in re.sub('[\W_]','',str.lower(str(html))):
        logger.log(DEBUG_OBSESSIVE,'No part number {} in HTML page from {} ({})'.format(pn, dist, url))
        raise PartHtmlError

    try:
        tree = BeautifulSoup(html, 'lxml')
    except Exception:
        logger.log(DEBUG_OBSESSIVE,'No HTML tree for {} from {}'.format(pn, dist))
        raise PartHtmlError

    # If the tree contains the tag for a product page, then just return it.
    if tree.find('div', id='ph') is not None:
        return tree, url

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('table', id="products") is not None:
        logger.log(DEBUG_OBSESSIVE,'Found product table for {} from {}'.format(pn, dist))
        if descend <= 0:
            logger.log(DEBUG_OBSESSIVE,'Passed descent limit for {} from {}'.format(pn, dist))
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
                        logger.log(DEBUG_OBSESSIVE,'Selecting {} from product table for {} from {}'.format(l.text, pn, dist))
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
                        return get_part_html_tree(dist, pn, extra_search_terms,
                                                  url=l.get('href', ''),
                                                  descend=descend-1,
                                                  scrape_retries=scrape_retries)
                except KeyError:
                    pass    # This happens if there is no 'href' in the link, so just skip it.

    # I don't know what happened here, so give up.
    logger.log(DEBUG_OBSESSIVE,'Unknown error for {} from {}'.format(pn, dist))
    raise PartHtmlError
