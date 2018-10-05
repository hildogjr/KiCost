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

# Python2/3 compatibility.
#from __future__ import unicode_literals, print_function, division, absolute_import
from future import standard_library
standard_library.install_aliases()

# Libraries.
import copy, re
import logging

# KiCost definitions.
from ..global_vars import logger, DEBUG_OVERVIEW, DEBUG_OBSESSIVE  # Debug configurations.
from ..global_vars import SEPRTR

# Distributors definitions.
from .distributor import distributor_class
from .global_vars import distributor_dict

from currency_converter import CurrencyConverter
currency_convert = CurrencyConverter().convert

__all__ = ['dist_local_template']

class dist_local_template(distributor_class):

    @staticmethod
    def dist_init_distributor_dict():
        distributor_dict.update({
            'local_template': {
                'octopart_name': '',
                'module': 'local', # The directory name containing this file.
                'type': 'local', # Allowable values: 'api', 'scrape' or 'local'.
                'order': {
                    'cols': ['part_num', 'purch', 'refs'],  # Sort-order for online orders.
                    'delimiter': ' '  # Delimiter for online orders.
                },
                'label': {
                    'name': 'Local',  # Distributor label used in spreadsheet columns.
                    # Formatting for distributor header in worksheet; bold, font and align are
                    # `spreadsheet.py` defined but can by overload heve.
                    'format': { 'font_color': 'white', 'bg_color': '#008000'},  # Darker green.
                },
            }
        })

    def query_part_info(parts, distributors, currency='USD'):
        """Fill-in part information for locally-sourced parts not handled by Octopart."""

        # This loops through all the parts and finds any that are sourced from
        # local distributors that are not normally searched and places them into
        # the distributor disctionary.
        for part in parts:
            # Find the various distributors for this part by
            # looking for leading fields terminated by SEPRTR.
            for key in part.fields:
                try:
                    dist = key[:key.index(SEPRTR)]
                except ValueError:
                    continue

                # If the distributor is not in the list of web-scrapable distributors,
                # then it's a local distributor. Copy the local distributor template
                # and add it to the table of distributors.
                if dist not in distributors:
                    distributors[dist] = copy.deepcopy(distributors['local_template'])
                    distributors[dist]['label']['name'] = dist  # Set dist name for spreadsheet header.

        # Set part info to default values for all the distributors.
        for part in parts:
            part.part_num = {dist: '' for dist in distributors}
            part.url = {dist: '' for dist in distributors}
            part.price_tiers = {dist: {} for dist in distributors}
            part.qty_avail = {dist: None for dist in distributors}
            part.qty_increment = {dist: None for dist in distributors}
            part.info_dist = {dist: {} for dist in distributors}

        # Loop through the parts looking for those sourced by local distributors
        # that won't be found online. Place any user-added info for these parts
        # (such as pricing) into the part dictionary.
        for p in parts:
            # Find the manufacturer's part number if it exists.
            pn = p.fields.get('manf#')  # Returns None if no manf# field.

            # Now look for catalog number, price list and webpage link for this part.
            for dist in distributors:
                cat_num = p.fields.get(dist + ':cat#')
                pricing = p.fields.get(dist + ':pricing')
                link = p.fields.get(dist + ':link')
                if cat_num is None and pricing is None and link is None:
                    continue

                def make_random_catalog_number(p):
                    FIELDS_MANFCAT = ([d + '#' for d in distributor_dict] + ['manf#'])
                    FIELDS_NOT_HASH = (['manf#_qty', 'manf'] + FIELDS_MANFCAT + [d + '#_qty' for d in distributor_dict])
                    #TODO unify the `FIELDS_NOT_HASH` configuration (used also in `edas/tools.py`).
                    hash_fields = {k: p.fields[k] for k in p.fields if k not in FIELDS_NOT_HASH}
                    hash_fields['dist'] = dist
                    return '#{0:08X}'.format(abs(hash(tuple(sorted(hash_fields.items())))))

                cat_num = cat_num or pn or make_random_catalog_number(p)
                p.fields[dist + ':cat#'] = cat_num  # Store generated cat#.
                p.part_num[dist] = cat_num

                try:
                    url_parts = list(urlsplit(link))
                    if url_parts[0] == '':
                        url_parts[0] = u'http'
                    link = urlunsplit(url_parts)
                except Exception:
                    # This happens when no part URL is found.
                    logger.log(DEBUG_OBSESSIVE, 'No local part URL found!')
                p.url[dist] = link

                price_tiers = {}
                try:
                    local_currency = re.findall('\w{3}', pricing)
                    pricing = re.sub(
                        '[^0-9.;:]', '',
                        pricing)  # Keep only digits, decimals, delimiters.
                    for qty_price in pricing.split(';'):
                        qty, price = qty_price.split(SEPRTR)
                        if local_currency and local_currency[0]!=currency.upper():
                            try:
                                price = currency_convert(price, local_currency[0], currency.upper())
                            except:
                                pass
                        price_tiers[int(qty)] = float(price)
                except AttributeError:
                    # This happens when no pricing info is found.
                    logger.log(DEBUG_OBSESSIVE,
                               'No local pricing information found!')
                p.price_tiers[dist] = price_tiers

        # Remove the local distributor template so it won't be processed later on.
        # It has served its purpose.
        try:
            del distributors['local_template']
        except:
            pass
