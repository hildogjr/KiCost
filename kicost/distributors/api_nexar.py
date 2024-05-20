# -*- coding: utf-8 -*-
# Nexar API implementation, replaces Octopart API
#
# MIT license
#
# Copyright (C) 2022 by Salvador E. Tropea / Instituto Nacional de Tecnologia Industrial
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
#
# I took the basic query from  https://github.com/NexarDeveloper/nexar-first-supply-query.git
# and the example in Nexar's IDE
# The class is based on the api_partinfo_kitspace.py class
#
# Important note:
# We get offers from tons of distributors, there is no way to say which ones we want.
# In:
# https://support.nexar.com/support/solutions/articles/101000434623-how-can-i-get-an-exact-manufacturer-match-with-specific-suppliers
# Suggests to use:
# options: {filters: {distributor_id: ["459", "1106", "2401", "2628", "2454", "3261", "12947"]}}
# But this isn't a "hard" filter, according to the support people you must filter it anyways.

# Author information.
__author__ = 'Salvador Eduardo Tropea'
__webpage__ = 'https://github.com/set-soft'
__company__ = 'Instituto Nacional de Tecnologia Industrial - Argentina'

# Libraries.
import copy
import difflib
import json
import os
import pprint
import re
import requests
import sys
import time
from collections import OrderedDict
if sys.version_info[0] < 3:
    from urllib import quote_plus
else:
    from urllib.parse import quote_plus

# KiCost definitions.
from .. import KiCostError, DistData, DEFAULT_CURRENCY, ERR_SCRAPE, W_NOINFO, NO_PRICE, W_APIFAIL, W_AMBIPN
# Distributors definitions.
from .distributor import distributor_class, QueryCache, hide_secrets
from .log__ import debug_overview, debug_obsessive, warning


# Uncomment for debug
# Use `debug('x + 1')` for instance.
# def debug(expression):
#     frame = sys._getframe(1)
#     distributor_class.logger.info(expression, '=', repr(eval(expression, frame.f_globals, frame.f_locals)))

MAX_PARTS_PER_QUERY = 20  # Maximum number of parts in a single query.

# Information to return from Nexar API
QUERY_ANSWER = '''
    hits,
    reference,
    parts {
      id,
      slug,
      mpn,
      manufacturer {name, id},
      shortDescription,
      specs {
        attribute {shortname, name, id},
        displayValue
      },
      octopartUrl,
      bestDatasheet {name, url},
      sellers(authorizedOnly: false) {
        company {name, id},
        offers {
            sku,
            id,
            inventoryLevel,
            moq,
            orderMultiple,
            packaging,
            prices {quantity, price, currency},
            onOrderQuantity,
            clickUrl
        }
      }
    }
'''
QUERY_ANSWER = re.sub(r'[\s\n]', '', QUERY_ANSWER)


QUERY_MATCH = ('query MultiMatchSearch($queries: [SupPartMatchQuery!]!) {'
               'supMultiMatch(queries: $queries, country: "@COUNTRY@", currency: "@CUR@") {' +
               QUERY_ANSWER + '} }')
QUERY_URL = 'https://api.nexar.com/graphql'
PROD_TOKEN_URL = 'https://identity.nexar.com/connect/token'
# Specs known by KiCost
SPEC_NAMES = {'tolerance': 'tolerance',
              'frequency': 'frequency',
              'powerrating': 'power',
              'voltagerating': 'voltage',
              'temperaturecoefficient': 'temp_coeff',
              'case_package': 'footprint',
              'maxdccurrent': 'current',
              'forwardcurrent': 'current',
              'currentrating': 'current'}


__all__ = ['api_nexar']


class QueryStruct(object):
    def __init__(self, id, part, for_dists, seller=None, sku=None, manf=None, mpn=None):
        self.id = 'q'+str(id)
        query = OrderedDict()
        query["reference"] = self.id
        query["start"] = 0
        query["limit"] = 5
        self.seller = seller
        self.sku = sku
        self.manf = manf
        self.mpn = mpn
        if sku is not None:
            query['seller'] = seller
            query['sku'] = sku
        elif mpn is not None:
            if manf:
                query['manufacturer'] = manf
            query['mpn'] = mpn
        self.query = query  # The query dict
        self.part = part    # Pointer to the part.
        self.for_dists = for_dists  # List of distributors we want for this query
        self.result = None
        self.loaded = False

    def remove_manufacturer(self):
        self.manf = None
        del self.query['manufacturer']


class api_nexar(distributor_class):
    name = 'Nexar'
    type = 'api'
    enabled = True
    url = 'https://nexar.com/api'  # Web site API information.
    id = None
    secret = None
    country = 'US'
    env_prefix = 'NEXAR'
    env_ops = {'NEXAR_STORAGE_PATH': 'cache_path'}

    # This is what we used for Octopart
    # https://octopart.com/api/v4/values#sellers
    api_distributors = ['arrow', 'digikey', 'farnell', 'lcsc', 'mouser', 'newark', 'rs', 'tme']
    DIST_TRANSLATION = {  # Distributor translation. Just a few supported.
                        'Arrow Electronics': 'arrow',
                        'Digi-Key': 'digikey',
                        'Farnell': 'farnell',
                        'Mouser': 'mouser',
                        'Newark': 'newark',
                        'RS Components': 'rs',
                        'TME': 'tme',
                        'LCSC': 'lcsc',
                       }
    # Dict to translate KiCost field names into KitSpace distributor names
    KICOST2NEXAR_DIST = {v: k for k, v in DIST_TRANSLATION.items()}
    cache = None
    config_options = {'client_id': str, 'client_secret': str, 'country': str}
    # Token
    expiration = 0
    token = None
    access_token = None

    @staticmethod
    def configure(ops):
        cache_ttl = 7
        cache_path = None
        for k, v in ops.items():
            if k == 'enable':
                api_nexar.enabled = v
            elif k == 'cache_ttl':
                cache_ttl = v
            elif k == 'cache_path':
                cache_path = v
            elif k == 'client_id':
                api_nexar.id = v
            elif k == 'client_secret':
                api_nexar.secret = v
            elif k == 'country':
                api_nexar.country = v
        if api_nexar.enabled and (api_nexar.id is None or api_nexar.secret is None or cache_path is None):
            warning(W_APIFAIL, "Can't enable Nexar without a `client_id`, `client_secret` and `cache_path`")
            api_nexar.enabled = False
        debug_obsessive('Nexar API configured to enabled {} id {} secret {} path {}'.
                        format(api_nexar.enabled, hide_secrets(api_nexar.id), hide_secrets(api_nexar.secret), cache_path))
        if not api_nexar.enabled:
            return
        api_nexar.cache = QueryCache(cache_path, cache_ttl)

    @staticmethod
    def get_token():
        """ Return the Nexar token from the client_id and client_secret provided """
        token = {}
        try:
            token = requests.post(url=PROD_TOKEN_URL,
                                  data={"grant_type": "client_credentials",
                                        "client_id": api_nexar.id,
                                        "client_secret": api_nexar.secret},
                                  allow_redirects=False).json()
        except Exception as e:
            raise KiCostError('Error getting token from Nexar ({})'.format(e), ERR_SCRAPE)
        debug_obsessive('Nexar token {}'.format(token))
        return token

    @staticmethod
    def get_headers():
        """ Get the access token, make sure it isn't expired """
        if os.environ.get('KICOST_NEXAR_NO_TOKEN', None):
            # No token for debug
            return {}
        if api_nexar.expiration < time.time() + 300:
            api_nexar.token = api_nexar.get_token()
            api_nexar.access_token = api_nexar.token.get('access_token')
            api_nexar.expiration = time.time() + api_nexar.token.get('expires_in', 0)
        return {'token': api_nexar.access_token}

    @staticmethod
    def query(query_parts, currency, query_type=QUERY_MATCH):
        """ Send query to server and return results. """
        # Allow changing the URL for debug purposes
        try:
            url = os.environ['KICOST_NEXAR_URL']
        except KeyError:
            url = QUERY_URL
        query_type = query_type.replace('@COUNTRY@', api_nexar.country)
        query_type = query_type.replace('@CUR@', currency)
        variables = {"queries": query_parts}
        # Remove all spaces, even inside the manf#
        # SET comment: this is how the code always worked. Octopart (used by KitSpace) ignores spaces inside manf# codes.
        # Do the query using POST
        data = 'query={}&variables={}'.format(quote_plus(query_type), quote_plus(str(variables)))
        distributor_class.log_request(url, data)
        data = OrderedDict()
        data["query"] = query_type
        data["variables"] = variables
        response = requests.post(url, json=data, headers=api_nexar.get_headers())
        response.encoding = 'UTF-8'
        distributor_class.log_response(response)
        if response.status_code == requests.codes['ok']:  # 200
            results = json.loads(response.text)
            if 'errors' in results:
                raise KiCostError('\n'.join((e['message'] for e in results['errors'])), ERR_SCRAPE)
            return results
        elif response.status_code == requests.codes['not_found']:  # 404
            raise KiCostError('Nexar server not found check your internet connection.', ERR_SCRAPE)
        elif response.status_code == requests.codes['request_timeout']:  # 408
            raise KiCostError('Nexar is not responding.', ERR_SCRAPE)
        elif response.status_code == requests.codes['bad_request']:  # 400
            raise KiCostError('Bad request to Nexar server probably due to an incorrect string '
                              'format check your `manf#` codes and contact the suport team.', ERR_SCRAPE)
        elif response.status_code == requests.codes['gateway_timeout']:  # 504
            raise KiCostError('One of the internal Nexar services may experiencing problems.', ERR_SCRAPE)
        else:
            raise KiCostError('Nexar error: ' + str(response.status_code), ERR_SCRAPE)

    @staticmethod
    def get_spec(data, item, default=None):
        '''Get the value of `value` field of a dictionary if the `name` field identifier.
        Used to get information from the JSON response.'''
        for d in data['specs']:
            if d['attribute']['shortname'] == item:
                return d.get('displayValue', default)
        return default

    @staticmethod
    def query2name(q):
        ''' Finds the prefix and name for a query '''
        if q.mpn is not None:
            prefix = 'mpn'
            name = (q.manf if q.manf else 'unk') + '_' + q.mpn
        elif q.sku is not None:
            prefix = 'sku'
            name = (q.seller if q.seller else 'unk') + '_' + q.sku
        name = name.replace(' ', '_')
        return prefix, name

    @staticmethod
    def get_part_info(queries, currency, to_retry):
        '''Query PartInfo for quantity/price info.
           `distributors` is the list of all distributors we want, in general. '''
        only_query = [q.query for q in queries]
        results = api_nexar.query(only_query, currency)
        for i, r in enumerate(results['data']['supMultiMatch']):
            q = queries[i]
            q.result = r
            assert r['reference'] == q.id, 'Out of order results, please report'
            # Solve the prefix and name
            prefix, name = api_nexar.query2name(q)
            api_nexar.cache.save_results(prefix, name, r)
            if not r.get('hits') and q.mpn is not None and q.manf:
                # Found, but has no hits
                # Try without specifying a manufacturer
                q.remove_manufacturer()
                to_retry.append(q)

    @staticmethod
    def fill_extra_info(result, specs, extra_info):
        # We fill only missing information, the mandatory info comes from the original distributor
        if 'desc' not in extra_info:
            desc = result.get('shortDescription')
            if desc:
                extra_info['desc'] = desc
        if 'manf' not in extra_info:
            manf = result.get('manufacturer', {}).get('name')
            if manf:
                extra_info['manf'] = manf
        if 'value' not in extra_info:
            value = ''
            for spec in ('capacitance', 'resistance', 'inductance'):
                val = specs.get(spec, None)
                if val:
                    value += val[1] + ' '
            if value:
                extra_info['value'] = value
        if 'size' not in extra_info:
            size = ''
            le = specs.get('length')
            if le:
                size += 'L: '+le[1]+' '
            w = specs.get('width')
            if w:
                size += 'W: '+w[1]+' '
            h = specs.get('height')
            if h:
                size += 'H: '+h[1]
            if size:
                extra_info['size'] = size
        for spec, name in SPEC_NAMES.items():
            if name in extra_info:
                continue
            val = specs.get(spec, None)
            if val:
                extra_info[name] = val[1]

    @staticmethod
    def select_best_part(result, part, native_dists):
        """ Select the best part, we discard results that are not distributed by our distributors.
            Then we look for the one that best matches the `manf`. """
        hits = result['hits']
        debug_obsessive('Hits: {}'.format(hits))
        # Each result can match one or more components from different manufacturers
        # Take only the items with useful offers
        useful_items = []
        for item in result['parts']:
            for offer in item['sellers']:
                if offer['company']['name'] in native_dists:
                    useful_items.append(item)
                    break
        # debug_obsessive(str(result))
        # debug_obsessive(str(useful_items))
        # If more than one select the best
        no_offers = False
        if len(useful_items) > 1:
            # List of possible manufacturers
            manufacturers = {}
            for it in useful_items:
                manf = it['manufacturer']['name'].lower()
                if manf not in manufacturers:
                    # We store the only the first one
                    # Nexar provides the best entry first, and sometimes an optional entry
                    # Example: Vishay CRCW06030000Z0EA vs Vishay CRCW0603-0000Z0EA
                    manufacturers[manf] = it
            # Is the manf included?
            manf = part.fields.get('manf', 'none').lower()
            item = manufacturers.get(manf)
            if not item:
                if manf == 'none':
                    item = useful_items[0]
                else:
                    best_matches = difflib.get_close_matches(manf, manufacturers.keys())
                    if best_matches:
                        item = manufacturers[best_matches[0]]
                    else:
                        item = useful_items[0]
                mpn = item['mpn']
                warning(W_AMBIPN, 'Using "{}" for manf#="{}"'.format(item['manufacturer']['name'], mpn))
                warning(W_AMBIPN, 'Ambiguous manf#="{}" please use manf to select the right one, choices: {}'.format(
                        mpn, list(manufacturers.keys())))
        else:
            if len(useful_items):
                item = useful_items[0]
            else:
                item = result['parts'][0]
                no_offers = True
        return item, no_offers

    @staticmethod
    def fill_part_data(part, result):
        ''' Fill generic data in the PartGroup() structure '''
        # Get the information of the part.
        # Datasheet, only if we don't have one
        if not part.datasheet:
            best_datasheet = result.get('bestDatasheet')
            if best_datasheet:
                part.datasheet = best_datasheet.get('url')
        # Life cycle
        lifecycle = api_nexar.get_spec(result, 'lifecyclestatus', '')
        if not lifecycle:
            lifecycle = api_nexar.get_spec(result, 'manufacturerlifecyclestatus', '')
        if lifecycle:
            # End Of Live -> obsolete
            lifecycle = lifecycle.replace('EOL ', 'obsolete ')
            part.lifecycle = lifecycle
        # Misc data collected, currently not used inside KiCost
        part.update_specs({sp['attribute']['shortname']: (sp['attribute']['name'], sp['displayValue'])
                          for sp in result['specs'] if sp['displayValue']})

    @staticmethod
    def fill_part_info(queries, distributors, currency, solved):
        ''' Place the results into the parts list. '''
        # Translate from PartInfo distributor names to the names used internally by kicost.
        dist_xlate = api_nexar.DIST_TRANSLATION

        # Loop through the response to the query and enter info into the parts list.
        for q in queries:
            # Unpack the structure
            part_query = q.query
            part = q.part
            dist_want = q.for_dists
            result = q.result
            # Process it
            if not result or not result.get('hits'):
                warning(W_NOINFO, 'No information found for parts \'{}\' query `{}`'.format(part.refs, str(part_query)))
                continue
            # Select the best hit
            native_dists = set((api_nexar.KICOST2NEXAR_DIST[d] for d in dist_want))
            result, no_offers = api_nexar.select_best_part(result, part, native_dists)
            # Note that it could have no useful offers, in this case we extract some info and then skip it
            api_nexar.fill_part_data(part, result)
            if no_offers:
                continue
            # Loop through the offers from various dists for this particular part.
            for offer in result['sellers']:
                # Get the distributor who made the offer and add their
                # price/qty info to the parts list if its one of the accepted distributors.
                dist = dist_xlate.get(offer['company']['name'], '')
                if dist not in dist_want:
                    # Not interested in this distributor
                    # debug_obsessive('Discard offer: {}'.format(offer['company']['name']))
                    continue
                # Get the DistData for this distributor
                dd = part.dd.get(dist, DistData())
                # Extra information
                api_nexar.fill_extra_info(result, part.specs, dd.extra_info)
                # Each distributor (seller) can have one or more offers
                for of in offer['offers']:
                    # Get pricing information from this distributor.
                    # The offer could contain more than one currency, so we separate the prices by currency.
                    dist_currency = {}
                    for pr in of['prices']:
                        cur = pr['currency']
                        ne = (pr['quantity'], pr['price'])
                        if cur in dist_currency:
                            dist_currency[cur].append(ne)
                        else:
                            dist_currency[cur] = [ne]
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
                    part_qty_increment = of.get('orderMultiple', 1)
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
                    dist_part_num = of.get('sku', '')
                    qty_avail = dd.qty_avail
                    in_stock_quantity = of.get('inventoryLevel')
                    if not qty_avail or (in_stock_quantity and qty_avail < in_stock_quantity):
                        # Keeps the information of more availability.
                        dd.qty_avail = in_stock_quantity  # In stock.
                    ign_stock_code = distributor_class.get_distributor_info(dist).ignore_cat
                    valid_part = not (ign_stock_code and re.match(ign_stock_code, dist_part_num))
                    # debug('dd.part_num')  # Uncomment to debug
                    # debug('dd.qty_increment')  # Uncomment to debug
                    moq = of.get('moq')
                    if (valid_part and
                        (not dd.part_num or
                         (dd.qty_increment is None or part_qty_increment < dd.qty_increment) or
                         (not dd.moq or (moq and dd.moq > moq)))):
                        # Save the link, stock code, ... of the page for minimum purchase.
                        dd.moq = moq  # Minimum order qty.
                        dd.url = of.get('clickUrl', '')  # Page to purchase the minimum quantity.
                        dd.part_num = dist_part_num
                        dd.qty_increment = part_qty_increment
                    # Update the DistData for this distributor
                    part.dd[dist] = dd
                # We have data for this distributor
                solved.add(dist)

    @staticmethod
    def look_query_in_cache(query, unsolved):
        # Solve the prefix and name
        prefix, name = api_nexar.query2name(query)
        # Look in the cache
        query.result, query.loaded = api_nexar.cache.load_results(prefix, name)
        if not query.loaded:
            unsolved.append(query)
        else:
            debug_obsessive('Data from cache: '+pprint.pformat(query.result))

    @staticmethod
    def solve_queries(unsolved, n_unsolved, currency):
        to_retry = []
        # Setup progress bar to track progress of server queries.
        progress = distributor_class.progress(n_unsolved, distributor_class.logger)

        # Slice the queries into batches of the largest allowed size and gather
        # the part data for each batch.
        for i in range(0, n_unsolved, MAX_PARTS_PER_QUERY):
            slc = slice(i, i+MAX_PARTS_PER_QUERY)
            api_nexar.get_part_info(unsolved[slc], currency, to_retry)
            progress.update(len(unsolved[slc]))

        # Done with the scraping progress bar so delete it or else we get an
        # error when the program terminates.
        progress.close()
        return to_retry, len(to_retry)

    @staticmethod
    def query_part_info(parts, distributors, currency):
        '''Fill-in the parts with price/qty/etc info from Nexar.'''
        debug_overview('# Getting part data from Nexar ...')

        # Use just the distributors avaliable in this API.
        # Note: The user can use --exclude and define it with fields.
        distributors = [d for d in distributors if distributor_class.get_distributor_info(d).is_web()
                        and d in api_nexar.api_distributors]
        FIELDS_CAT = sorted([d + '#' for d in distributors])

        # Create queries to get part price/quantities from PartInfo.
        queries = []
        # Translate from PartInfo distributor names to the names used internally by kicost.
        available_distributors = set(api_nexar.api_distributors)
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
                        part_code_dist = api_nexar.KICOST2NEXAR_DIST[part_catalogue_code_dist]
                        queries.append(QueryStruct(len(queries), part, [part_catalogue_code_dist], seller=part_code_dist, sku=part_stock))
                        part_dist_use_manfpn.remove(part_catalogue_code_dist)
                else:
                    found_codes_for_all_dists = False

            # Create a query using the manufacturer P/N
            part_manf = part.fields.get('manf', '')
            part_code = part.fields.get('manf#')
            if part_code and not found_codes_for_all_dists:
                # Not all distributors has code, add a query for the manufaturer P/N
                # List of distributors without an specific part number
                queries.append(QueryStruct(len(queries), part, part_dist_use_manfpn, manf=part_manf, mpn=part_code))

        n_queries = len(queries)
        debug_overview('Queries {}'.format(n_queries))
        if not n_queries:
            return

        # Try to solve the queries from the cache
        unsolved = []
        for query in queries:
            api_nexar.look_query_in_cache(query, unsolved)
            if query.loaded and not query.result.get('hits') and query.mpn is not None and query.manf:
                # Found, but has no hits
                # Try without specifying a manufacturer
                query.remove_manufacturer()
                api_nexar.look_query_in_cache(query, unsolved)

        # Solve the rest from the site
        n_unsolved = len(unsolved)
        debug_overview('Cached entries {} (of {})'.format(n_queries-n_unsolved, n_queries))
        if n_unsolved:
            unsolved, n_unsolved = api_nexar.solve_queries(unsolved, n_unsolved, currency)
            # Do we need to retry some queries?
            if n_unsolved:
                unsolved, n_unsolved = api_nexar.solve_queries(unsolved, n_unsolved, currency)

        # Transfer the results
        solved_dist = set()
        api_nexar.fill_part_info(queries, distributors, currency, solved_dist)
        return solved_dist


distributor_class.register(api_nexar, 75)
