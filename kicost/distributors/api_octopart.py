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

# Libraries.
import json
import requests
import re
import os
import sys
import difflib
from collections import Counter
if sys.version_info[0] < 3:
    from urllib import quote_plus
else:
    from urllib.parse import quote_plus

# KiCost definitions.
from .. import KiCostError, DistData, ERR_SCRAPE, W_ASSQTY, W_AMBIPN, W_APIFAIL
# Distributors definitions.
from .distributor import distributor_class, QueryCache
from .log__ import debug_overview, debug_obsessive, warning

# Author information.
__author__ = 'XESS Corporation'
__webpage__ = 'info@xess.com'

OCTOPART_MAX_PARTBYQUERY = 20  # Maximum part list length to one single query.

__all__ = ['api_octopart']


class QueryStruct(object):
    def __init__(self, id, kind, code, part):
        self.id = str(id)  # ID number for this query
        self.kind = kind   # mpn/sku
        self.code = code   # manf_code/sku
        self.part = part   # Pointer to the part.
        self.result = None
        self.loaded = False


class api_octopart(distributor_class):
    name = 'Octopart'
    type = 'api'
    enabled = False
    url = 'https://octopart.com/'  # Web site API information.
    # Options supported by this API
    config_options = {'key': str, 'level': int, 'extended': bool}
    api_level = 4
    # Include specs and datasheets. Only in the Pro plan.
    extended = False
    cache = None

    API_KEY = None
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
    # Dict to translate KiCost field names into Octopart distributor names
    KICOST2OCTOPART_DIST = {v: k for k, v in DIST_TRANSLATION.items()}

    @staticmethod
    def configure(ops):
        cache_ttl = 7
        cache_path = None
        for k, v in ops.items():
            if k == 'key':
                api_octopart.API_KEY = v
                if 'enable' not in ops:
                    # If not explicitly disabled then enable it
                    api_octopart.enabled = True
            elif k == 'enable':
                api_octopart.enabled = v
            elif k == 'extended':
                api_octopart.extended = v
            elif k == 'level':
                api_octopart.api_level = v
            elif k == 'cache_ttl':
                cache_ttl = v
            elif k == 'cache_path':
                cache_path = v
        api_octopart.cache = QueryCache(cache_path, cache_ttl)
        if api_octopart.enabled and api_octopart.API_KEY is None:
            warning(W_APIFAIL, "Can't enable Octopart without a `key`")
            api_octopart.enabled = False
        debug_obsessive('Octopart API configured to enabled {} key {} level {} extended {}'.
                        format(api_octopart.enabled, api_octopart.API_KEY, api_octopart.api_level, api_octopart.extended))

    @staticmethod
    def query(query):
        """Send query to Octopart and return results."""
        # url = 'http://octopart.com/api/v3/parts/match'
        # payload = {'queries': json.dumps(query), 'include\[\]': 'specs', 'apikey': token}
        # response = requests.get(url, params=payload)
        data = 'queries=['+', '.join(query)+']'
        if api_octopart.API_KEY:
            if api_octopart.api_level == 3:
                url = 'http://octopart.com/api/v3/parts/match'
            else:
                url = 'http://octopart.com/api/v4/rest/parts/match'
            data += '&apikey=' + api_octopart.API_KEY
        else:  # Not working 2021/04/28:
            url = 'https://temp-octopart-proxy.kitspace.org/parts/match'
        # Allow changing the URL for debug purposes
        try:
            url = os.environ['KICOST_OCTOPART_URL']
        except KeyError:
            pass
        if api_octopart.extended:
            data += '&include[]=specs'
            data += '&include[]=datasheets'
        distributor_class.log_request(url, data)
        response = requests.get(url + '?' + data)
        distributor_class.log_response(response)
        if response.status_code == 200:  # Ok
            results = json.loads(response.text).get('results')
            return results
        elif response.status_code == 400:  # Bad request
            raise KiCostError('Octopart missing apikey.', ERR_SCRAPE)
        elif response.status_code == 404:  # Not found
            raise KiCostError('Octopart server not found.', ERR_SCRAPE)
        elif response.status_code == 403 or 'Invalid API key' in response.text:
            raise KiCostError('Octopart KEY invalid, register one at "https://www.octopart.com".', ERR_SCRAPE)
        elif response.status_code == 429:  # Too many requests
            raise KiCostError('Octopart request limit reached.', ERR_SCRAPE)
        else:
            raise KiCostError('Octopart error: ' + str(response.status_code), ERR_SCRAPE)

    @staticmethod
    def sku_to_mpn(sku):
        """Find manufacturer part number associated with a distributor SKU."""
        part_query = ['{"reference": "1", "sku": "'+quote_plus(sku)+'"}']
        results = api_octopart.query(part_query)
        if not results:
            return None
        result = results[0]
        mpns = [item['mpn'] for item in result['items']]
        if not mpns:
            return None
        if len(mpns) == 1:
            return mpns[0]
        mpn_cnts = Counter(mpns)
        return mpn_cnts.most_common(1)[0][0]  # Return the most common MPN.

    @staticmethod
    def skus_to_mpns(parts, distributors):
        """Find manufaturer's part number for all parts with just distributor SKUs."""
        for i, part in enumerate(parts):

            # Skip parts that already have a manufacturer's part number.
            if part.fields.get('manf#'):
                continue

            # Get all the SKUs for this part.
            skus = list(
                set([part.fields.get(dist + '#', '') for dist in distributors]))
            skus = [sku for sku in skus
                    if sku not in ('', None)]  # Remove null SKUs.

            # Skip this part if there are no SKUs.
            if not skus:
                continue

            # Convert the SKUs to manf. part numbers.
            mpns = [api_octopart.sku_to_mpn(sku) for sku in skus]
            mpns = [mpn for mpn in mpns
                    if mpn not in ('', None)]  # Remove null manf#.

            # Skip assigning manf. part number to this part if there aren't any to assign.
            if not mpns:
                continue

            # Assign the most common manf. part number to this part.
            mpn_cnts = Counter(mpns)
            part.fields['manf#'] = mpn_cnts.most_common(1)[0][0]

    @staticmethod
    def get_part_info(queries):
        """Query Octopart for quantity/price info."""
        only_query = ['{"reference": "'+q.id+'", "'+q.kind+'": "'+quote_plus(q.code)+'"}' for q in queries]
        results = api_octopart.query(only_query)
        # Copy the results to the queries
        q_hash = {q.id: q for q in queries}
        for r in results:
            query = q_hash[r['reference']]
            query.result = r
            api_octopart.cache.save_results(query.kind, query.code, r)

    @staticmethod
    def fill_part_info(queries, distributors, solved, currency='USD'):
        ''' Place the results into the parts list. '''
        # Translate from Octopart distributor names to the names used internally by kicost.
        dist_xlate = api_octopart.DIST_TRANSLATION
        # List of desired distributors in native format
        native_dists = set((api_octopart.KICOST2OCTOPART_DIST[d] for d in distributors))
        # Currency priority: 1: User specified, 2: USD, 3: EUR
        currency_prio = [currency]
        if currency != 'USD':
            currency_prio.append('USD')
        if currency != 'EUR':
            currency_prio.append('EUR')
        # Loop through the response to the query and enter info into the parts list.
        for query in queries:
            result = query.result
            part = query.part
            # Each result can match one or more components from different manufacturers
            # Take only the items with useful offers
            useful_items = []
            for item in result['items']:
                for offer in item['offers']:
                    if offer['seller']['name'] in native_dists:
                        useful_items.append(item)
                        break
            # debug_obsessive(str(result))
            # debug_obsessive(str(useful_items))
            # If more than one select the right one
            if len(useful_items) > 1:
                # List of possible manufacturers
                # TODO: Can we get more than one hit for the same manf?
                manufacturers = {it['manufacturer']['name'].lower(): it for it in useful_items}
                # Is the manf included?
                manf = part.fields.get('manf', 'none').lower()
                item = manufacturers.get(manf)
                if not item:
                    if manf == 'none':
                        item = useful_items[0]
                    else:
                        best_match = difflib.get_close_matches(manf, manufacturers.keys())[0]
                        item = manufacturers[best_match]
                    mpn = item['mpn']
                    warning(W_AMBIPN, 'Using "{}" for manf#="{}"'.format(item['manufacturer']['name'], mpn))
                    warning(W_AMBIPN, 'Ambiguous manf#="{}" please use manf to select the right one, choices: {}'.format(
                            mpn, list(manufacturers.keys())))
            else:
                if len(useful_items):
                    item = useful_items[0]
                else:
                    # No hits, skip
                    continue
            if api_octopart.extended:
                # Assign the lifecycle status 'obsolete' (others possible: 'active' and 'not recommended for new designs') but not used.
                try:
                    # API v4 (production, eol, nrnd, ...) we take the first word
                    part.lifecycle = item['specs']['lifecyclestatus']['value'][0].lower().split(' ')[0]
                except KeyError:
                    try:
                        # API v3
                        part.lifecycle = item['specs']['lifecycle_status']['value'][0].lower()
                    except KeyError:
                        # No lifecyclestatus (current name) nor lifecycle_status (old name)
                        pass
                # Take the datasheet provided by the distributor. This will by used
                # in the output spreadsheet if not provide any in the BOM/schematic.
                # This will be signed in the file.
                try:
                    part.datasheet = item['datasheets'][0]['url']
                except (KeyError, IndexError):
                    # No datasheet key (KeyError) or empty (IndexError)
                    pass
                # Misc data collected, currently not used inside KiCost
                part.update_specs({code: (info['metadata']['name'], ', '.join(info['value'])) for code, info in item['specs'].items()})
            # Loop through the offers from various dists for this particular part.
            for offer in item['offers']:
                # Get the distributor who made the offer and add their
                # price/qty info to the parts list if its one of the accepted distributors.
                dist = dist_xlate.get(offer['seller']['name'], '')
                if dist not in distributors:
                    # Unknown or excluded seller
                    continue
                price_tiers = {}
                part_qty_increment = float("inf")
                # Get the DistData for this distributor
                dd = part.dd.get(dist, DistData())
                # Get pricing information from this distributor.
                prices = offer['prices']
                if prices:
                    for curr in currency_prio:
                        if curr in prices:
                            dd.currency = curr
                            price_l = prices[curr]
                            break
                    else:
                        # Use the first entry
                        dd.currency, price_l = next(iter(prices.items()))
                    price_tiers = {qty: float(price) for qty, price in price_l}
                    # Combine price lists for multiple offers from the same distributor
                    # to build a complete list of cut-tape and reeled components.
                    dd.price_tiers.update(price_tiers)
                    # Compute the quantity increment between the lowest two prices.
                    # This will be used to distinguish the cut-tape from the reeled components.
                    try:
                        part_break_qtys = sorted(price_tiers.keys())
                        part_qty_increment = part_break_qtys[1] - part_break_qtys[0]
                    except IndexError:
                        # This will happen if there are not enough entries in the price/qty list.
                        # As a stop-gap measure, just assign infinity to the part increment.
                        # A better alternative may be to examine the packaging field of the offer.
                        pass
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
                if not dd.part_num:
                    qty_avail = dd.qty_avail
                    in_stock_quantity = offer.get('in_stock_quantity')
                    if not qty_avail or (in_stock_quantity and qty_avail < in_stock_quantity):
                        # Keep the information with more availability.
                        dd.qty_avail = in_stock_quantity
                    moq = dd.moq
                    moq_offer = offer.get('moq')
                    if not moq or (moq_offer and moq > moq_offer):
                        # Save the link, stock code, ... of the page for minimum purchase.
                        dd.moq = moq_offer  # Minimum order qty.
                        dd.part_num = offer.get('sku')
                        dd.url = offer.get('product_url')
                        dd.qty_increment = part_qty_increment
                # Otherwise, check qty increment and see if its the smallest for this part & dist.
                elif part_qty_increment < dd.qty_increment:
                    # This part looks more like a cut-tape version, so
                    # update the SKU, web page, and available quantity.
                    qty_avail = dd.qty_avail
                    in_stock_quantity = offer.get('in_stock_quantity')
                    if not qty_avail or (in_stock_quantity and qty_avail < in_stock_quantity):
                        # Keep the information with more availability.
                        dd.qty_avail = in_stock_quantity
                    # Check for a valid SKU
                    dist_part_num = offer.get('sku', '')
                    ign_stock_code = distributor_class.get_distributor_info(dist).ignore_cat
                    valid_part = not (ign_stock_code and re.match(ign_stock_code, dist_part_num))
                    moq_offer = offer.get('moq')
                    if (valid_part and (not dd.part_num or (part_qty_increment < dd.qty_increment) or
                                        (not dd.moq or (moq_offer and dd.moq > moq_offer)))):
                        # Save the link, stock code, ... of the page for minimum purchase.
                        dd.moq = moq_offer  # Minimum order qty.
                        dd.part_num = dist_part_num
                        dd.url = offer.get('product_url')
                        dd.qty_increment = part_qty_increment
                # Update the DistData for this distributor
                part.dd[dist] = dd
                # We have data for this distributor
                solved.add(dist)

    @staticmethod
    def query_part_info(parts, distributors, currency):
        """Fill-in the parts with price/qty/etc info from Octopart."""
        debug_overview('# Getting part data from Octopart...')

        # Get the valid distributors names used by them part catalog
        # that may be index by Octopart. This is used to remove the
        # local distributors and future not implemented in the Octopart
        # definition.
        # Note: The user can use --exclude and define it with fields.
        distributors_octopart = [d for d in distributors if distributor_class.get_distributor_info(d).is_web()
                                 and d in api_octopart.api_distributors]

        # Collect all the queries
        queries = []
        for i, part in enumerate(parts):
            # Create an Octopart query using the manufacturer's part number or distributor SKU.
            manf_code = part.fields.get('manf#')
            if manf_code:
                query = QueryStruct(i, "mpn", manf_code, part)
            else:
                # No MPN, so use the first distributor SKU that's found.
                for octopart_dist_sku in distributors_octopart:
                    sku = part.fields.get(octopart_dist_sku + '#', '')
                    if sku:
                        break
                if not sku:
                    # No MPN or SKU, so skip this part.
                    continue
                # Create the part query using SKU matching.
                query = QueryStruct(i, "sku", sku, part)

                # Because was used the distributor (enrolled at Octopart list)
                # despite the normal 'manf#' code, take the sub quantity as
                # general sub quantity of the current part.
                try:
                    part.fields['manf#_qty'] = part.fields[octopart_dist_sku + '#_qty']
                    warning(W_ASSQTY, "Associated {q} quantity to '{r}' due \"{f}#={q}:{c}\".".format(
                            q=part.fields[octopart_dist_sku + '#_qty'], r=part.refs,
                            f=octopart_dist_sku, c=part.fields[octopart_dist_sku+'#']))
                except KeyError:
                    pass
            # Add query for this part to the list of part queries.
            queries.append(query)

        n_queries = len(queries)
        debug_overview('Queries {}'.format(n_queries))
        if not n_queries:
            return

        # Try to solve the queries from the cache
        unsolved = []
        for query in queries:
            # Look in the cache
            query.result, query.loaded = api_octopart.cache.load_results(query.kind, query.code)
            if not query.loaded:
                unsolved.append(query)

        # Solve the rest from the site
        n_unsolved = len(unsolved)
        debug_overview('Cached entries {}'.format(n_queries-n_unsolved))
        if n_unsolved:
            # Setup progress bar to track progress of server queries.
            progress = distributor_class.progress(n_unsolved, distributor_class.logger)

            # Slice the queries into batches of the largest allowed size and gather
            # the part data for each batch.
            for i in range(0, n_unsolved, OCTOPART_MAX_PARTBYQUERY):
                slc = slice(i, i+OCTOPART_MAX_PARTBYQUERY)
                api_octopart.get_part_info(unsolved[slc])
                progress.update(len(unsolved[slc]))

            # Done with the scraping progress bar so delete it or else we get an
            # error when the program terminates.
            progress.close()

        # Transfer the results
        solved_dist = set()
        api_octopart.fill_part_info(queries, distributors_octopart, solved_dist, currency)
        return solved_dist

    @staticmethod
    def from_environment(options, overwrite):
        ''' Configuration from the environment. '''
        # Configure the module from the environment
        # The command line will overwrite it using set_options()
        key = os.getenv('KICOST_OCTOPART_KEY_V3')
        if key:
            api_octopart._set_from_env('key', key, options, overwrite)
            api_octopart._set_from_env('enable', True, options, overwrite)
            api_octopart._set_from_env('level', 3, options, overwrite)
        else:
            key = os.getenv('KICOST_OCTOPART_KEY_V4')
            if key:
                api_octopart._set_from_env('key', key, options, overwrite)
                api_octopart._set_from_env('enable', True, options, overwrite)
                api_octopart._set_from_env('level', 4, options, overwrite)
            elif os.environ.get('KICOST_OCTOPART'):
                # Currently this isn't useful, you can't do anything without a key.
                # This is just in case we get a proxy running.
                api_octopart._set_from_env('enable', True, options, overwrite)
        if os.environ.get('KICOST_OCTOPART_EXTENDED'):
            api_octopart._set_from_env('extended', True, options, overwrite)


distributor_class.register(api_octopart, 60)
