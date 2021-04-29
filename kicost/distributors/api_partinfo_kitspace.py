# -*- coding: utf-8 -*-
# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Max Maisel / Hildo Guillardi Júnior
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

from __future__ import print_function

# Author information.
__author__ = 'Hildo Guillardi Júnior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# Libraries.
import json
import requests
import logging
import tqdm
import re
import sys
import os
import copy
from collections import OrderedDict
if sys.version_info[0] < 3:
    from urllib import quote_plus
else:
    from urllib.parse import quote_plus

# KiCost definitions.
from ..global_vars import DEFAULT_CURRENCY, DEBUG_OVERVIEW
# Distributors definitions.
from .distributor import distributor_class


# Use `debug('x + 1')` for instance.
def debug(expression):
    frame = sys._getframe(1)
    print(expression, '=', repr(eval(expression, frame.f_globals, frame.f_locals)))


MAX_PARTS_PER_QUERY = 20  # Maximum number of parts in a single query.

# Information to return from PartInfo KitSpace server.

QUERY_AVAIABLE_CURRENCIES = ['GBP', 'EUR', 'USD']
# DEFAULT_CURRENCY
QUERY_ANSWER = '''
    mpn{manufacturer, part},
    datasheet,
    description,
    specs{key, value},
    offers(from: {DISTRIBUTORS}){
        product_url,
        sku {vendor, part},
        description,
        moq,
        in_stock_quantity,
        prices{''' + ','.join(QUERY_AVAIABLE_CURRENCIES) + '''}
        }
'''
# Informations not used: type,specs{key, name, value},image {url, credit_string, credit_url},stock_location
QUERY_ANSWER = re.sub(r'[\s\n]', '', QUERY_ANSWER)

QUERY_PART = 'query ($input: MpnInput!) { part(mpn: $input) {' + QUERY_ANSWER + '} }'
QUERY_MATCH = 'query ($input: [MpnOrSku]!){ match(parts: $input) {' + QUERY_ANSWER + '} }'
QUERY_SEARCH = 'query ($input: String!){ search(term: $input) {' + QUERY_ANSWER + '} }'
QUERY_URL = 'https://dev-partinfo.kitspace.org/graphql'

__all__ = ['api_partinfo_kitspace']


class TqdmLoggingHandler(logging.Handler):
    '''Overload the class to write the logging through the `tqdm`.'''
    def __init__(self, level=logging.NOTSET):
        super(self.__class__, self).__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)
        pass


class api_partinfo_kitspace(distributor_class):
    name = 'KitSpace'
    type = 'api'
    enabled = True
    url = 'https://kitspace.org/'  # Web site API information.

    API_DISTRIBUTORS = ['digikey', 'farnell', 'mouser', 'newark', 'rs', 'arrow', 'tme', 'lcsc']
    DIST_TRANSLATION = {  # Distributor translation.
                        'Digikey': 'digikey',
                        'Farnell': 'farnell',
                        'Mouser': 'mouser',
                        'Newark': 'newark',
                        'RS': 'rs',
                        'TME': 'tme',
                        'Arrow Electronics, Inc.': 'arrow',
                        'LCSC': 'lcsc',
                       }
    # Dict to translate KiCost field names into KitSpace distributor names
    KICOST2KITSPACE_DIST = {v: k for k, v in DIST_TRANSLATION.items()}

    @staticmethod
    def init_dist_dict():
        if api_partinfo_kitspace.enabled:
            distributor_class.add_distributors(api_partinfo_kitspace.API_DISTRIBUTORS)

    @staticmethod
    def query(query_parts, distributors, query_type=QUERY_MATCH):
        '''Send query to server and return results.'''

        distributors = [api_partinfo_kitspace.KICOST2KITSPACE_DIST[d] for d in distributors]
        # Allow changing the URL for debug purposes
        try:
            url = os.environ['KICOST_KITSPACE_URL']
        except KeyError:
            url = QUERY_URL
        # Sort the distributors to create a reproducible query
        query_type = re.sub(r'\{DISTRIBUTORS\}', '["' + '","'.join(sorted(distributors)) + '"]', query_type)
        # r = requests.post(url, {"query": QUERY_SEARCH, "variables": variables}) #TODO future use for ISSUE #17
        variables = '{"input":[' + ','.join(query_parts) + ']}'
        # Remove all spaces, even inside the manf#
        # SET comment: this is how the code always worked. Octopart (used by KitSpace) ignores spaces inside manf# codes.
        variables = variables.replace(' ', '')
        # Do the query using POST
        data = 'query={}&variables={}'.format(quote_plus(query_type), quote_plus(variables))
        distributor_class.log_request(url, data)
        data = OrderedDict()
        data["query"] = query_type
        data["variables"] = variables
        response = requests.post(url, data)
        distributor_class.log_response(response.text)
        if response.status_code == requests.codes['ok']:  # 200
            results = json.loads(response.text)
            return results
        elif response.status_code == requests.codes['not_found']:  # 404
            raise Exception('Kitspace server not found check your internet connection.')
        elif response.status_code == requests.codes['request_timeout']:  # 408
            raise Exception('KitSpace is not responding.')
        elif response.status_code == requests.codes['bad_request']:  # 400
            raise Exception('Bad request to Kitspace server probably due to an incorrect string format check your `manf#` codes and contact the suport team.')
        elif response.status_code == requests.codes['gateway_timeout']:  # 504
            raise Exception('One of the internal Kitspace services may experiencing problems. Contact the Kitspace support.')
        else:
            raise Exception('Kitspace error: ' + str(response.status_code))

    @staticmethod
    def get_value(data, item, default=None):
        '''Get the value of `value` field of a dictionary if the `name`field identifier.
        Used to get information from the JSON response.'''
        try:
            for d in data:
                try:
                    if d['key'] == item:
                        return d['value']
                except KeyError:
                    continue
            return default
        except Exception:
            return default

    @staticmethod
    def get_part_info(query, parts, distributors, currency, distributor_info=None):
        '''Query PartInfo for quantity/price info and place it into the parts list.
           `distributor_info` is used to update only one distributor information (price_tiers, ...),
           the proposed if use in the disambiguation procedure.
        '''
        # Translate from PartInfo distributor names to the names used internally by kicost.
        dist_xlate = api_partinfo_kitspace.DIST_TRANSLATION

        results = api_partinfo_kitspace.query(query, distributors)
        if not distributor_info:
            distributor_info = [None] * len(query)

        # Loop through the response to the query and enter info into the parts list.
        for part_query, part, dist_info, result in zip(query, parts, distributor_info, results['data']['match']):

            if not result:
                distributor_class.logger.warning('No information found for parts \'{}\' query `{}`'.format(part.refs, str(part_query)))

            else:

                # Get the information of the part.
                part.datasheet = result.get('datasheet')
                part.lifecycle = api_partinfo_kitspace.get_value(result['specs'], 'lifecycle_status', 'active')

                # Loop through the offers from various dists for this particular part.
                for offer in result['offers']:
                    # Get the distributor who made the offer and add their
                    # price/qty info to the parts list if its one of the accepted distributors.
                    dist = dist_xlate.get(offer['sku']['vendor'], '')
                    if dist_info and dist not in dist_info:
                        continue
                    if dist not in distributors:
                        continue
                    # Get pricing information from this distributor.
                    try:
                        price_tiers = {}  # Empty dict in case of exception.
                        if not offer['prices']:
                            distributor_class.logger.warning('No price information found for parts \'{}\' query `{}`'.format(part.refs, str(part_query)))
                        else:
                            dist_currency = list(offer['prices'].keys())

                            # Get the price tiers prioritizing:
                            # 1) The asked currency by KiCost user;
                            # 2) The default currency given by `DEFAULT_CURRENCY` in root `global_vars.py`;
                            # 3) The first not null tier.s
                            prices = None
                            if currency in dist_currency and offer['prices'][currency]:
                                prices = offer['prices'][currency]
                                part.currency[dist] = currency
                            elif DEFAULT_CURRENCY in dist_currency and offer['prices'][DEFAULT_CURRENCY]:  # and DEFAULT_CURRENCY!=currency:
                                prices = offer['prices'][DEFAULT_CURRENCY]
                                part.currency[dist] = DEFAULT_CURRENCY
                            else:
                                for dist_c in dist_currency:
                                    if offer['prices'][dist_c]:
                                        prices = offer['prices'][dist_c]
                                        part.currency[dist] = dist_c
                                        break

                            # Some times the API returns minimum purchase 0 and a not valid `price_tiers`.
                            if prices:
                                price_tiers = {qty: float(price) for qty, price in list(prices)}
                                # Combine price lists for multiple offers from the same distributor
                                # to build a complete list of cut-tape and reeled components.
                                if dist not in part.price_tiers:
                                    part.price_tiers[dist] = {}
                                part.price_tiers[dist].update(price_tiers)
                    except TypeError:
                        pass  # Price list is probably missing so leave empty default dict in place.

                    # Compute the quantity increment between the lowest two prices.
                    # This will be used to distinguish the cut-tape from the reeled components.
                    try:
                        part_break_qtys = sorted(price_tiers.keys())
                        part_qty_increment = part_break_qtys[1] - part_break_qtys[0]
                    except IndexError:
                        # This will happen if there are not enough entries in the price/qty list.
                        # As a stop-gap measure, just assign infinity to the part increment.
                        # A better alternative may be to examine the packaging field of the offer.
                        part_qty_increment = float("inf")

                    # Select the part SKU, web page, and available quantity.
                    # Each distributor can have different stock codes for the same part in different
                    # quantities / delivery package styles: cut-tape, reel, ...
                    # Therefore we select and overwrite a previous selection if one of the
                    # following conditions is met:
                    #   1. We don't have a selection for this part from this distributor yet.
                    #   2. The MOQ is smaller than for the current selection.
                    #   3. The part_qty_increment for this offer smaller than that of the existing selection.
                    #      (we prefer cut-tape style packaging over reels)
                    #   4. For DigiKey, we can't use part_qty_increment to distinguish between
                    #      reel and cut-tape, so we need to look at the actual DigiKey part number.
                    #      This procedure is made by the definition `distributors_info[dist]['ignore_cat#_re']`
                    #      at the distributor profile.
                    dist_part_num = offer.get('sku', '').get('part', '')
                    qty_avail = part.qty_avail.get(dist)
                    if not qty_avail or (offer.get('in_stock_quantity') and qty_avail < offer.get('in_stock_quantity')):
                        # Keeps the information of more availability.
                        part.qty_avail[dist] = offer.get('in_stock_quantity')  # In stock.
                    ign_stock_code = distributor_class.get_distributor_info(dist).get('ignore_cat#_re', '')
                    valid_part = not (ign_stock_code and re.match(ign_stock_code, dist_part_num))
                    # debug('part.part_num[dist]') # Uncomment to debug
                    # debug('part.qty_increment[dist]')  # Uncomment to debug
                    if (valid_part and
                        (not part.part_num.get(dist) or
                         (part.qty_increment.get(dist) is None or part_qty_increment < part.qty_increment.get(dist)) or
                         (not part.moq.get(dist) or (offer.get('moq') and part.moq.get(dist) > offer.get('moq'))))):
                        # Save the link, stock code, ... of the page for minimum purchase.
                        part.moq[dist] = offer.get('moq')  # Minimum order qty.
                        part.url[dist] = offer.get('product_url', '')  # Page to purchase the minimum quantity.
                        part.part_num[dist] = dist_part_num
                        part.qty_increment[dist] = part_qty_increment

                    # Don't bother with any extra info from the distributor.
                    part.info_dist[dist] = {}

    @staticmethod
    def query_part_info(parts, distributors, currency):
        '''Fill-in the parts with price/qty/etc info from KitSpace.'''
        distributor_class.logger.log(DEBUG_OVERVIEW, '# Getting part data from KitSpace...')

        # Change the logging print channel to `tqdm` to keep the process bar to the end of terminal.
        # Get handles to default sys.stdout logging handler and the
        # new "tqdm" logging handler.
        if len(distributor_class.logger.handlers) > 0:
            logDefaultHandler = distributor_class.logger.handlers[0]
            logTqdmHandler = TqdmLoggingHandler()
            # Replace default handler with "tqdm" handler.
            distributor_class.logger.addHandler(logTqdmHandler)
            distributor_class.logger.removeHandler(logDefaultHandler)

        # Use just the distributors avaliable in this API.
        # Note: The user can use --exclude and define it with fields.
        distributors = [d for d in distributors if distributor_class.get_distributor_info(d)['type'] == 'web'
                        and d in api_partinfo_kitspace.API_DISTRIBUTORS]
        FIELDS_CAT = sorted([d + '#' for d in distributors])

        # Create queries to get part price/quantities from PartInfo.
        queries = []  # Each part reference query.
        query_parts = []  # Pointer to the part.
        query_part_stock_code = []  # Used the stock code mention for disambiguation, it is used `None` for the "manf#".
        # Translate from PartInfo distributor names to the names used internally by kicost.
        available_distributors = set(api_partinfo_kitspace.API_DISTRIBUTORS)
        for part in parts:
            # Create a PartInfo query using the manufacturer's part number or the distributor's SKU.
            part_dist_use_manfpn = copy.copy(distributors)

            # Check if that part have stock code that is accepted to use by this module (API).
            # KiCost will prioritize these codes under "manf#" that will be used for get
            # information for the part hat were not filled with the distributor stock code. So
            # this is checked after the 'manf#' buv code.
            found_codes_for_all_dists = True
            for d in FIELDS_CAT:
                part_stock = part.fields.get(d)
                if part_stock:
                    part_catalogue_code_dist = d[:-1]
                    if part_catalogue_code_dist in available_distributors:
                        part_code_dist = api_partinfo_kitspace.KICOST2KITSPACE_DIST[part_catalogue_code_dist]
                        queries.append('{"sku":{"vendor":"' + part_code_dist + '","part":"' + part_stock + '"}}')
                        query_parts.append(part)
                        query_part_stock_code.append(part_catalogue_code_dist)
                        part_dist_use_manfpn.remove(part_catalogue_code_dist)
                else:
                    found_codes_for_all_dists = False

            part_manf = part.fields.get('manf', '')
            part_code = part.fields.get('manf#')
            if part_code and not found_codes_for_all_dists:
                # Not all distributors has code, include the manufaturer P/N
                queries.append('{"mpn":{"manufacturer":"' + part_manf + '","part":"' + part_code + '"}}')
                query_parts.append(part)
                # List of distributors without an specific part number
                query_part_stock_code.append(part_dist_use_manfpn)

        # Setup progress bar to track progress of server queries.
        progress = tqdm.tqdm(desc='Progress', total=len(query_parts), unit='part', miniters=1)

        # Slice the queries into batches of the largest allowed size and gather
        # the part data for each batch.
        for i in range(0, len(queries), MAX_PARTS_PER_QUERY):
            slc = slice(i, i+MAX_PARTS_PER_QUERY)
            api_partinfo_kitspace.get_part_info(queries[slc], query_parts[slc], distributors, currency, query_part_stock_code[slc])
            progress.update(len(queries[slc]))

        # Restore the logging print channel now that the progress bar is no longer needed.
        if len(distributor_class.logger.handlers) > 0:
            distributor_class.logger.addHandler(logDefaultHandler)
            distributor_class.logger.removeHandler(logTqdmHandler)

        # Done with the scraping progress bar so delete it or else we get an
        # error when the program terminates.
        del progress


distributor_class.register(api_partinfo_kitspace, 50)
