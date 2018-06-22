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
from yattag import Doc, indent # For generating HTML page for local parts.
import copy # To be possible create more than one local distributor.
from ...global_vars import PartHtmlError
from ...global_vars import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE
from ...global_vars import SEPRTR as SEPRTR

from .. import distributor
from ..global_vars import distributor_dict

from urllib.parse import urlsplit, urlunsplit

class dist_local(distributor.distributor):
    # Static variable which contains local part html.
    html = None

    def __init__(self, name, scrape_retries, throttle_delay):
        super(dist_local, self).__init__(name, None, scrape_retries, throttle_delay)

    @staticmethod
    def dist_init_distributor_dict():
        distributor_dict.update(
        {
            'local_template': {
                'module': 'local', # The directory name containing this file.
                'scrape': 'local', # Allowable values: 'web' or 'local'.
                'label': 'Local',  # Distributor label used in spreadsheet columns.
                'order_cols': ['part_num', 'purch', 'refs'],  # Sort-order for online orders.
                'order_delimiter': ' ',  # Delimiter for online orders.
                # Formatting for distributor header in worksheet.
                'wrk_hdr_format': {
                    'font_size': 14,
                    'font_color': 'white',
                    'bold': True,
                    'align': 'center',
                    'valign': 'vcenter',
                    'bg_color': '#008000'  # Darker green.
                },
            }
        })

    @staticmethod
    def create_part_html(parts, distributors, logger):
        '''@brief Create HTML page containing info for local (non-webscraped) parts.
        @param parts `list()` of parts.
        @parm `list()`of the distributors to check each one is local.
        @param logger
        '''
        
        logger.log(DEBUG_OVERVIEW, 'Create HTML page for parts with custom pricing...')
        
        doc, tag, text = Doc().tagtext()
        with tag('html'):
            with tag('body'):
                for p in parts:
                    # Find the manufacturer's part number if it exists.
                    pn = p.fields.get('manf#') # Returns None if no manf# field.

                    # Find the various distributors for this part by
                    # looking for leading fields terminated by SEPRTR.
                    for key in p.fields:
                        try:
                            dist = key[:key.index(SEPRTR)]
                        except ValueError:
                            continue

                        # If the distributor is not in the list of web-scrapable distributors,
                        # then it's a local distributor. Copy the local distributor template
                        # and add it to the table of distributors.
                        if dist not in distributors:
                            distributors[dist] = copy.copy(distributors['local_template'])
                            distributors[dist]['label'] = dist  # Set dist name for spreadsheet header.

                    # Now look for catalog number, price list and webpage link for this part.
                    for dist in distributors:
                        cat_num = p.fields.get(dist+':cat#')
                        pricing = p.fields.get(dist+':pricing')
                        link = p.fields.get(dist+':link')
                        if cat_num is None and pricing is None and link is None:
                            continue

                        def make_random_catalog_number(p):
                            hash_fields = {k: p.fields[k] for k in p.fields}
                            hash_fields['dist'] = dist
                            return '#{0:08X}'.format(abs(hash(tuple(sorted(hash_fields.items())))))

                        cat_num = cat_num or pn or make_random_catalog_number(p)
                        p.fields[dist+':cat#'] = cat_num # Store generated cat#.
                        with tag('div', klass=dist+SEPRTR+cat_num):
                            with tag('div', klass='cat#'):
                                text(cat_num)
                            if pricing is not None:
                                with tag('div', klass='pricing'):
                                    text(pricing)
                            if link is not None:
                                url_parts = list(urlsplit(link))
                                if url_parts[0] == '':
                                    url_parts[0] = u'http'
                                link = urlunsplit(url_parts)
                                with tag('div', klass='link'):
                                    text(link)

        # Remove the local distributor template so it won't be processed later on.
        # It has served its purpose.
        try:
            del distributors['local_template']
        except:
            pass

        dist_local.html = doc.getvalue()
        if logger.isEnabledFor(DEBUG_OBSESSIVE):
            print(indent(dist_local.html))


    def dist_get_price_tiers(self, html_tree):
        '''@brief Get the pricing tiers from the parsed tree of the local product page.
           @param html_tree `str()` html of the distributor part page.
           @return `dict()` price breaks, the keys are the quantities breaks.
        '''
        price_tiers = {}
        try:
            pricing = html_tree.find('div', class_='pricing').text
            pricing = re.sub('[^0-9.;:]', '', pricing) # Keep only digits, decimals, delimiters.
            for qty_price in pricing.split(';'):
                qty, price = qty_price.split(SEPRTR)
                price_tiers[int(qty)] = float(price)
        except AttributeError:
            # This happens when no pricing info is found in the tree.
            self.logger.log(DEBUG_OBSESSIVE, 'No local pricing information found!')
            return price_tiers  # Return empty price tiers.
        return price_tiers


    def dist_get_part_num(self, html_tree):
        '''@brief Get the part number from the local product page.
           @param html_tree `str()` html of the distributor part page.
           @return `list()`of the parts that match.
        '''
        try:
            part_num_str = html_tree.find('div', class_='cat#').text
            return part_num_str
        except AttributeError:
            return ''


    def dist_get_qty_avail(self, html_tree):
        '''@brief Get the available quantity of the part from the local product page.
           @param html_tree `str()` html of the distributor part page.
           @return `int` avaliable quantity.
        '''
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
            self.logger.log(DEBUG_OBSESSIVE, 'No local part quantity found!')
            return 0

    def dist_get_part_html_tree(self, pn, extra_search_terms='', url=None, descend=None):
        '''Extract the HTML tree from the HTML page for local parts.
           @param pn Part number `str()`.
           @param extra_search_terms
           @param url
           @param descend
           @return (html `str()` of the page, `None`) The second argument is always `None` bacause there is not url to return.
        '''

        # Extract the HTML tree from the local part HTML page.
        try:
            tree = BeautifulSoup(dist_local.html, 'lxml')
        except Exception:
            raise PartHtmlError

        try:
            # Find the DIV in the tree for the given part and distributor.
            class_ = self.name + SEPRTR + pn
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
