# -*- coding: utf-8 -*-

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

# Libraries.
import re
import sys
import hashlib

from .. import DistData, SEPRTR, W_BADPRICE
# Distributors definitions.
from .distributor import distributor_class
from .log__ import debug_overview, debug_obsessive, warning

__all__ = ['dist_local_template']

if sys.version_info[0] < 3:
    from urlparse import urlsplit, urlunsplit

    def to_bytes(val):
        return val
else:
    from urllib.parse import urlsplit, urlunsplit

    def to_bytes(val):
        return val.encode('utf-8')


unique_catalogs = {}


def make_unique_catalog_number(p, dist):
    FIELDS_MANFCAT = ([d + '#' for d in distributor_class.get_distributors_iter()] + ['manf#'])
    FIELDS_NOT_HASH = (['manf#_qty', 'manf'] + FIELDS_MANFCAT + [d + '#_qty' for d in distributor_class.get_distributors_iter()])
    # TODO unify the `FIELDS_NOT_HASH` configuration (used also in `edas/tools.py`).
    hash_fields = {k: p.fields[k] for k in p.fields if k not in FIELDS_NOT_HASH}
    hash_fields['dist'] = dist
    id = hashlib.md5(to_bytes(str(tuple(sorted(hash_fields.items()))))).hexdigest()
    num = unique_catalogs.get(id)
    if num is None:
        num = len(unique_catalogs) + 1
        unique_catalogs[id] = num
    return '#NO_CATALOG%04d' % num


class dist_local_template(distributor_class):
    name = 'Local'
    type = 'local'
    enabled = True
    url = None
    # We don't add distributors here, they are collected in query_part_info
    api_distributors = []

    @staticmethod
    def configure(ops):
        for k, v in ops.items():
            if k == 'enable':
                dist_local_template.enabled = v
        debug_obsessive('Local API configured to enabled {}'.format(dist_local_template.enabled))

    @staticmethod
    def update_distributors(parts, distributors):
        """ Looks for user defined distributors """
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
                # Note: If the user excludes a web-scrapable distributors (using --exclude)
                # and then adds it as a local distributor (using fields) it will be added.
                if dist not in distributors:
                    debug_overview('Creating \'{}\' local distributor profile...'.format(dist))
                    new_dist = distributor_class.get_distributor_template('local_template')
                    new_dist.label.name = dist  # Set dist name for spreadsheet header.
                    distributor_class.add_distributor(dist, new_dist)
                    distributors.append(dist)
                    dist_local_template.api_distributors.append(dist)

    @staticmethod
    def query_part_info(parts, distributors, currency):
        """ Fill-in part information for locally-sourced parts not handled by Octopart. """
        solved = set()
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

                cat_num = cat_num or pn or make_unique_catalog_number(p, dist)
                p.fields[dist + ':cat#'] = cat_num  # Store generated cat#.
                # Get the DistData for this distributor
                dd = p.dd.get(dist, DistData())
                dd.part_num = cat_num

                if link:
                    url_parts = list(urlsplit(link))
                    if url_parts[0] == '':
                        url_parts[0] = u'http'
                    link = urlunsplit(url_parts)
                else:
                    # This happens when no part URL is found.
                    debug_obsessive('No part URL found for local \'{}\' distributor!'.format(dist))
                dd.url = link

                price_tiers = {}
                try:
                    local_currency = re.findall('[a-zA-Z]{3}', pricing)[0].upper()
                except Exception:
                    local_currency = currency
                old_pricing = pricing
                pricing = re.sub('[^0-9.;:]', '', pricing)  # Keep only digits, decimals, delimiters.
                for qty_price in pricing.split(';'):
                    splitted = qty_price.split(SEPRTR)
                    if len(splitted) == 2:
                        qty, price = splitted
                        if local_currency:
                            dd.currency = local_currency
                        try:
                            price_tiers[int(qty)] = float(price)
                        except ValueError:
                            warning(W_BADPRICE, 'Malformed pricing number: `{}` at {}'.format(old_pricing, p.refs))
                    else:
                        warning(W_BADPRICE, 'Malformed pricing entry: `{}` at {}'.format(qty_price, p.refs))
                # dd.moq = min(price_tiers.keys())
                if not price_tiers:
                    # This happens when no pricing info is found.
                    debug_obsessive('No pricing information found for local \'{}\' distributor!'.format(dist))
                dd.price_tiers = price_tiers
                # Update the DistData for this distributor
                p.dd[dist] = dd
                # We have data for this distributor. Avoid marking normal distributors.
                if dist in dist_local_template.api_distributors:
                    solved.add(dist)
        return solved


distributor_class.register(dist_local_template, 100)
