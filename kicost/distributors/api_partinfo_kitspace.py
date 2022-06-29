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

# Author information.
__author__ = 'Hildo Guillardi Júnior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# Libraries.
import json
import requests
import re
import sys
import os
import copy
import pprint
from collections import OrderedDict
if sys.version_info[0] < 3:
    from urllib import quote_plus
else:
    from urllib.parse import quote_plus

# KiCost definitions.
from .. import KiCostError, DistData, DEFAULT_CURRENCY, ERR_SCRAPE, W_NOINFO, NO_PRICE
# Distributors definitions.
from .distributor import distributor_class, QueryCache
from .log__ import debug_overview, debug_obsessive, warning


# Uncomment for debug
# Use `debug('x + 1')` for instance.
# def debug(expression):
#     frame = sys._getframe(1)
#     distributor_class.logger.info(expression, '=', repr(eval(expression, frame.f_globals, frame.f_locals)))

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


class QueryStruct(object):
    def __init__(self, query, part, for_dists):
        self.query = query  # Each part reference query.
        self.part = part    # Pointer to the part.
        self.for_dists = for_dists  # Used the stock code mention for disambiguation, it is used `None` for the "manf#".
        self.result = None
        self.loaded = False


class api_partinfo_kitspace(distributor_class):
    name = 'KitSpace'
    type = 'api'
    enabled = True
    url = 'https://kitspace.org/'  # Web site API information.

    api_distributors = ['digikey', 'farnell', 'mouser', 'newark', 'rs', 'arrow', 'tme', 'lcsc']
    DIST_TRANSLATION = {  # Distributor translation.
                        'Digikey': 'digikey',
                        'Farnell': 'farnell',
                        'Mouser': 'mouser',
                        'Newark': 'newark',
                        'RS': 'rs',
                        'TME': 'tme',
                        'Arrow Electronics': 'arrow',
                        'LCSC': 'lcsc',
                       }
    # Dict to translate KiCost field names into KitSpace distributor names
    KICOST2KITSPACE_DIST = {v: k for k, v in DIST_TRANSLATION.items()}
    cache = None

    @staticmethod
    def configure(ops):
        cache_ttl = 7
        cache_path = None
        for k, v in ops.items():
            if k == 'enable':
                api_partinfo_kitspace.enabled = v
            elif k == 'cache_ttl':
                cache_ttl = v
            elif k == 'cache_path':
                cache_path = v
        api_partinfo_kitspace.cache = QueryCache(cache_path, cache_ttl)
        debug_obsessive('KitSpace API configured to enabled {}'.format(api_partinfo_kitspace.enabled))

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
        response.encoding = 'UTF-8'
        distributor_class.log_response(response)
        if response.status_code == requests.codes['ok']:  # 200
            results = json.loads(response.text)
            return results
        elif response.status_code == requests.codes['not_found']:  # 404
            raise KiCostError('Kitspace server not found check your internet connection.', ERR_SCRAPE)
        elif response.status_code == requests.codes['request_timeout']:  # 408
            raise KiCostError('KitSpace is not responding.', ERR_SCRAPE)
        elif response.status_code == requests.codes['bad_request']:  # 400
            raise KiCostError('Bad request to Kitspace server probably due to an incorrect string '
                              'format check your `manf#` codes and contact the suport team.', ERR_SCRAPE)
        elif response.status_code == requests.codes['gateway_timeout']:  # 504
            raise KiCostError('One of the internal Kitspace services may experiencing problems.'
                              ' Most probably is saturated, please consider using other API.', ERR_SCRAPE)
        else:
            raise KiCostError('Kitspace error: ' + str(response.status_code), ERR_SCRAPE)

    @staticmethod
    def get_spec(data, item, default=None):
        '''Get the value of `value` field of a dictionary if the `name` field identifier.
        Used to get information from the JSON response.'''
        for d in data['specs']:
            if d['key'] == item:
                value = d['value']
                return value if value is not None else default
        return default

    @staticmethod
    def query2name(query):
        ''' Finds the prefix and name for a query '''
        q = json.loads(query)
        mpn = q.get('mpn', None)
        if mpn is not None:
            prefix = 'mpn'
            name = mpn['part']
        else:
            sku = q.get('sku', None)
            if sku is not None:
                prefix = 'sku'
                name = sku['vendor'] + '_' + sku['part']
        return prefix, name

    @staticmethod
    def get_part_info(queries, distributors):
        '''Query PartInfo for quantity/price info.
           `distributors` is the list of all distributors we want, in general. '''
        only_query = [q.query for q in queries]
        results = api_partinfo_kitspace.query(only_query, distributors)
        for i, r in enumerate(results['data']['match']):
            queries[i].result = r
            # Solve the prefix and name
            prefix, name = api_partinfo_kitspace.query2name(queries[i].query)
            api_partinfo_kitspace.cache.save_results(prefix, name, r)

    @staticmethod
    def fill_part_info(queries, distributors, currency, solved):
        ''' Place the results into the parts list. '''
        # Translate from PartInfo distributor names to the names used internally by kicost.
        dist_xlate = api_partinfo_kitspace.DIST_TRANSLATION

        # Loop through the response to the query and enter info into the parts list.
        for q in queries:
            # Unpack the structure
            part_query = q.query
            part = q.part
            dist_want = q.for_dists
            result = q.result
            # Process it
            if not result:
                warning(W_NOINFO, 'No information found for parts \'{}\' query `{}`'.format(part.refs, str(part_query)))
                continue
            # Get the information of the part.
            part.datasheet = result.get('datasheet')
            part.lifecycle = api_partinfo_kitspace.get_spec(result, 'lifecycle_status', 'active').lower()
            # Misc data collected, currently not used inside KiCost
            part.update_specs({sp['key']: (sp['key'], sp['value']) for sp in result['specs'] if sp['value']})
            # Loop through the offers from various dists for this particular part.
            for offer in result['offers']:
                # Get the distributor who made the offer and add their
                # price/qty info to the parts list if its one of the accepted distributors.
                dist = dist_xlate.get(offer['sku']['vendor'], '')
                if dist not in dist_want:
                    # Not interested in this distributor
                    continue
                # Get the DistData for this distributor
                dd = part.dd.get(dist, DistData())
                # This will happen if there are not enough entries in the price/qty list.
                # As a stop-gap measure, just assign infinity to the part increment.
                # A better alternative may be to examine the packaging field of the offer.
                part_qty_increment = float("inf")
                # Get pricing information from this distributor.
                dist_currency = {cur: pri for cur, pri in offer['prices'].items() if pri}
                if not dist_currency:
                    # Some times the API returns minimum purchase 0 and a not valid `price_tiers`.
                    warning(NO_PRICE, 'No price information found for parts \'{}\' query `{}`'.format(part.refs, str(part_query)))
                else:
                    prices = None
                    # Get the price tiers prioritizing:
                    # 1) The asked currency by KiCost user;
                    # 2) The default currency given by `DEFAULT_CURRENCY` in root `global_vars.py`;
                    # 3) The first not null tiers
                    if currency in dist_currency:
                        prices = dist_currency[currency]
                        dd.currency = currency
                    elif DEFAULT_CURRENCY in dist_currency:
                        prices = dist_currency[DEFAULT_CURRENCY]
                        dd.currency = DEFAULT_CURRENCY
                    else:
                        dd.currency, prices = next(iter(dist_currency.items()))
                    price_tiers = {qty: float(price) for qty, price in prices}
                    # Combine price lists for multiple offers from the same distributor
                    # to build a complete list of cut-tape and reeled components.
                    dd.price_tiers.update(price_tiers)
                    # Compute the quantity increment between the lowest two prices.
                    # This will be used to distinguish the cut-tape from the reeled components.
                    if len(price_tiers) > 1:
                        part_break_qtys = sorted(price_tiers.keys())
                        part_qty_increment = part_break_qtys[1] - part_break_qtys[0]
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
                qty_avail = dd.qty_avail
                in_stock_quantity = offer.get('in_stock_quantity')
                if not qty_avail or (in_stock_quantity and qty_avail < in_stock_quantity):
                    # Keeps the information of more availability.
                    dd.qty_avail = in_stock_quantity  # In stock.
                ign_stock_code = distributor_class.get_distributor_info(dist).ignore_cat
                valid_part = not (ign_stock_code and re.match(ign_stock_code, dist_part_num))
                # debug('dd.part_num')  # Uncomment to debug
                # debug('dd.qty_increment')  # Uncomment to debug
                moq = offer.get('moq')
                if (valid_part and
                    (not dd.part_num or
                     (dd.qty_increment is None or part_qty_increment < dd.qty_increment) or
                     (not dd.moq or (moq and dd.moq > moq)))):
                    # Save the link, stock code, ... of the page for minimum purchase.
                    dd.moq = moq  # Minimum order qty.
                    dd.url = offer.get('product_url', '')  # Page to purchase the minimum quantity.
                    dd.part_num = dist_part_num
                    dd.qty_increment = part_qty_increment
                # Update the DistData for this distributor
                part.dd[dist] = dd
                # We have data for this distributor
                solved.add(dist)

    @staticmethod
    def query_part_info(parts, distributors, currency):
        '''Fill-in the parts with price/qty/etc info from KitSpace.'''
        debug_overview('# Getting part data from KitSpace...')

        # Use just the distributors avaliable in this API.
        # Note: The user can use --exclude and define it with fields.
        distributors = [d for d in distributors if distributor_class.get_distributor_info(d).is_web()
                        and d in api_partinfo_kitspace.api_distributors]
        FIELDS_CAT = sorted([d + '#' for d in distributors])

        # Create queries to get part price/quantities from PartInfo.
        queries = []
        # Translate from PartInfo distributor names to the names used internally by kicost.
        available_distributors = set(api_partinfo_kitspace.api_distributors)
        for part in parts:
            # Create a PartInfo query using the manufacturer's part number or the distributor's SKU.
            part_dist_use_manfpn = copy.copy(distributors)

            # Create queries using the distributor SKU
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
                        query_text = '{"sku":{"vendor":"' + part_code_dist + '","part":"' + part_stock + '"}}'
                        queries.append(QueryStruct(query_text, part, [part_catalogue_code_dist]))
                        part_dist_use_manfpn.remove(part_catalogue_code_dist)
                else:
                    found_codes_for_all_dists = False

            # Create a query using the manufacturer P/N
            part_manf = part.fields.get('manf', '')
            part_code = part.fields.get('manf#')
            if part_code and not found_codes_for_all_dists:
                # Not all distributors has code, add a query for the manufaturer P/N
                query_text = '{"mpn":{"manufacturer":"' + part_manf + '","part":"' + part_code + '"}}'
                # List of distributors without an specific part number
                queries.append(QueryStruct(query_text, part, part_dist_use_manfpn))

        n_queries = len(queries)
        debug_overview('Queries {}'.format(n_queries))
        if not n_queries:
            return

        # Try to solve the queries from the cache
        unsolved = []
        for query in queries:
            # Solve the prefix and name
            prefix, name = api_partinfo_kitspace.query2name(query.query)
            # Look in the cache
            query.result, query.loaded = api_partinfo_kitspace.cache.load_results(prefix, name)
            if not query.loaded:
                unsolved.append(query)
            else:
                debug_obsessive('Data from cache: '+pprint.pformat(query.result))

        # Solve the rest from the site
        n_unsolved = len(unsolved)
        debug_overview('Cached entries {} (of {})'.format(n_queries-n_unsolved, n_queries))
        if n_unsolved:
            # Setup progress bar to track progress of server queries.
            progress = distributor_class.progress(n_unsolved, distributor_class.logger)

            # Slice the queries into batches of the largest allowed size and gather
            # the part data for each batch.
            for i in range(0, n_unsolved, MAX_PARTS_PER_QUERY):
                slc = slice(i, i+MAX_PARTS_PER_QUERY)
                api_partinfo_kitspace.get_part_info(unsolved[slc], distributors)
                progress.update(len(unsolved[slc]))

            # Done with the scraping progress bar so delete it or else we get an
            # error when the program terminates.
            progress.close()

        # Transfer the results
        solved_dist = set()
        api_partinfo_kitspace.fill_part_info(queries, distributors, currency, solved_dist)
        return solved_dist


distributor_class.register(api_partinfo_kitspace, 50)
