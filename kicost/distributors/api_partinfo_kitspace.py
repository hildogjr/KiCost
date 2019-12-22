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
import json, requests
import logging, tqdm
import copy, re
from collections import Counter
#from urllib.parse import quote_plus as urlquote

# KiCost definitions.
from .global_vars import * # Debug information, `distributor_dict` and `SEPRTR`.
from ..edas.tools import order_refs

# Distributors definitions.
from .distributor import distributor_class

MAX_PARTS_PER_QUERY = 20 # Maximum number of parts in a single query.

# Information to return from PartInfo KitSpace server.

QUERY_AVAIABLE_CURRENCIES = {'GBP', 'EUR', 'USD'}
#DEFAULT_CURRENCY
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
#Informations not used: type,specs{key, name, value},image {url, credit_string, credit_url},stock_location
QUERY_ANSWER = re.sub('[\s\n]', '', QUERY_ANSWER)

QUERY_PART = 'query ($input: MpnInput!) { part(mpn: $input) {' + QUERY_ANSWER + '} }'
QUERY_MATCH = 'query ($input: [MpnOrSku]!){ match(parts: $input) {' + QUERY_ANSWER + '} }'
QUERY_SEARCH = 'query ($input: String!){ search(term: $input) {' + QUERY_ANSWER + '} }'
QUERY_URL = 'https://dev-partinfo.kitspace.org/graphql'

__all__ = ['api_partinfo_kitspace']
from .distributors_info import distributors_info

class api_partinfo_kitspace(distributor_class):

    @staticmethod
    def init_dist_dict():
        api_distributors = ['digikey', 'farnell', 'mouser', 'newark', 'rs', 'lcsc']
        dists = {k:v for k,v in distributors_info.items() if k in api_distributors}
        if not 'enabled' in distributors_modules_dict['api_partinfo_kitspace']:
             # First module load.
            distributors_modules_dict.update({'api_partinfo_kitspace':{
                                            'type': 'api', 'url': 'https://kitspace.org/', # Web site API information.
                                            'distributors': dists.keys(), # Avaliable web distributors in this api.
                                            'enabled': True, # Default status of the module (it's load but can be not calle).
                                            'param': None, # Configuration parameters.
                                            'dist_translation': { # Distributor translation.
                                                                    'Digikey': 'digikey',
                                                                    'Farnell': 'farnell',
                                                                    'Mouser': 'mouser',
                                                                    'Newark': 'newark',
                                                                    'RS': 'rs',
                                                                    'LCSC': 'lcsc',
                                                                }
                                                }
                                            })
        # Update the `distributor_dict` with the available distributor in this module with the module is enabled.
        # It can be not enabled by the GUI saved configurations.
        if distributors_modules_dict['api_partinfo_kitspace']['enabled']:
            distributor_dict.update(dists)


    @staticmethod
    def query(query_parts, distributors, query_type=QUERY_MATCH):
        '''Send query to server and return results.'''
        
        ##TODO this `dist_xlate` have to be better coded into this file.
        dist_xlate = distributors_modules_dict['api_partinfo_kitspace']['dist_translation']
        def find_key(input_dict, value):
            return next((k for k, v in input_dict.items() if v == value), None)
        distributors = ([find_key(dist_xlate, d) for d in distributors])
        
        query_type = re.sub('\{DISTRIBUTORS\}', '["'+ '","'.join(distributors) +'"]' , query_type)
        #r = requests.post(QUERY_URL, {"query": QUERY_SEARCH, "variables": variables}) #TODO future use for ISSUE #17
        variables = re.sub('\'', '\"', str(query_parts))
        variables = re.sub('\s', '', variables)
        # Python 2 prepends a 'u' before the query strings and this makes PartInfo
        # complain, so remove them.
        variables = re.sub(':u"', ':"', variables)
        variables = re.sub('{u"', '{"', variables)
        variables = '{{"input":{}}}'.format(variables)
        response = requests.post(QUERY_URL, {'query': query_type, "variables": variables})
        if response.status_code == requests.codes['ok']: #200
            results = json.loads(response.text)
            return results
        elif response.status_code == requests.codes['not_found']: #404
            raise Exception('Kitspace server not found check your internet connection.')
        elif response.status_code == requests.codes['request_timeout']: #408
            raise Exception('KitSpace is not responding.')
        elif response.status_code == requests.codes['bad_request']: #400
            raise Exception('Bad request to Kitspace server probably due to an incorrect string format check your `manf#` codes and contact the suport team.')
        elif response.status_code == requests.codes['gateway_timeout']: # 504
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
                except:
                    continue
            return default
        except:
            return default

    @staticmethod
    def query_part_info(parts, distributors, currency=DEFAULT_CURRENCY):
        '''Fill-in the parts with price/qty/etc info from KitSpace.'''
        logger.log(DEBUG_OVERVIEW, '# Getting part data from KitSpace...')

        # Change the logging print channel to `tqdm` to keep the process bar to the end of terminal.
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
                except:
                    self.handleError(record)
                pass
        # Get handles to default sys.stdout logging handler and the
        # new "tqdm" logging handler.
        logDefaultHandler = logger.handlers[0]
        logTqdmHandler = TqdmLoggingHandler()
        # Replace default handler with "tqdm" handler.
        logger.addHandler(logTqdmHandler)
        logger.removeHandler(logDefaultHandler)

        FIELDS_CAT = ([d + '#' for d in distributor_dict])
        DISTRIBUTORS = ([d for d in distributor_dict])
        # Use just the distributors avaliable in this API.
        distributors = list( set(DISTRIBUTORS) &
            set(distributors_modules_dict['api_partinfo_kitspace']['distributors']) )

        # Translate from PartInfo distributor names to the names used internally by kicost.
        dist_xlate = distributors_modules_dict['api_partinfo_kitspace']['dist_translation']

        def get_part_info(query, parts, distributor_info=None):
            '''Query PartInfo for quantity/price info and place it into the parts list.
               `distributor_info` is used to update only one distributor information (price_tiers, ...),
               the proposed if use in the disambiguation procedure.
            '''

            results = api_partinfo_kitspace.query(query, distributors)
            if not distributor_info:
                distributor_info = [None] * len(query)

            # Loop through the response to the query and enter info into the parts list.
            for part_query, part, dist_info, result in zip(query, parts, distributor_info, results['data']['match']):

                if not result:
                    logger.warning('No information found for parts \'{}\' query `{}`'.format(order_refs(part.refs), str(part_query)))

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
                        if dist in distributors:

                            # Get pricing information from this distributor.
                            try:
                                price_tiers = {} # Empty dict in case of exception.
                                if not offer['prices']:
                                    logger.warning('No price information found for parts \'{}\' query `{}`'.format(order_refs(part.refs), str(part_query)))
                                else:
                                    dist_currency = list(offer['prices'].keys())
                                    
                                    # Get the price tiers prioritizing:
                                    # 1) The asked currency by KiCOst user;
                                    # 2) The default currency given by `DEFAULT_CURRENCY` in root `global_vars.py`;
                                    # 3) The first not null tier.s
                                    prices = None
                                    if currency in dist_currency and offer['prices'][currency]:
                                        prices = offer['prices'][currency]
                                        part.currency[dist] = currency
                                    elif DEFAULT_CURRENCY in dist_currency and offer['prices'][DEFAULT_CURRENCY]:# and DEFAULT_CURRENCY!=currency:
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
                                        price_tiers = {qty: float(price)
                                                            for qty, price in list(prices)
                                                      }
                                        # Combine price lists for multiple offers from the same distributor
                                        # to build a complete list of cut-tape and reeled components.
                                        if not dist in part.price_tiers:
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
                            # Each distributor can have differente stock codes for the same part in different
                            # quantities / delivery package styles: cut-tape, reel, ...
                            # Therefore we select and overwrite a previous selection if one of the
                            # following conditions is met:
                            #   1. We don't have a selection for this part from this ditributor yet.
                            #   2. The MOQ is smaller than for the current selection.
                            #   3. The part_qty_increment for this offer smaller than that of the existing selection.
                            #      (we prefer cut-tape style packaging over reels)
                            #   4. For DigiKey, we can't use part_qty_increment to distinguish between
                            #      reel and cut-tape, so we need to look at the actual DigiKey part number.
                            dist_part_num = offer.get('sku', '').get('part', '')
                            if not part.qty_avail[dist] or (offer.get('in_stock_quantity') and part.qty_avail[dist]<offer.get('in_stock_quantity')):
                                # Keeps the information of more availability.
                                part.qty_avail[dist] = offer.get('in_stock_quantity') # In stock.
                            if not part.part_num[dist] or \
                               (not part.moq[dist] or (offer.get('moq') and part.moq[dist]>offer.get('moq'))) or \
                               (part_qty_increment < part.qty_increment[dist]) or \
                               (dist == "digikey" and part.part_num[dist].endswith("DKR-ND") and dist_part_num.endswith("CT-ND")):
                                    # Save the link, stock code, ... of the page for minimum purchase.
                                    part.moq[dist] = offer.get('moq') # Minimum order qty.
                                    part.url[dist] = offer.get('product_url', '') # Page to purchase the minimum quantity.
                                    part.part_num[dist] = dist_part_num
                                    part.qty_increment[dist] = part_qty_increment

                            # Don't bother with any extra info from the distributor.
                            part.info_dist[dist] = {}

        # Get the valid distributor names used by them part catalog
        # that may be index by PartInfo. This is used to remove the
        # local distributors and future not implemented in the PartInfo
        # definition.
        distributors_name_api = distributors_modules_dict['api_partinfo_kitspace']['dist_translation'].values()

        # Create queries to get part price/quantities from PartInfo.
        queries = [] # Each part reference query.
        query_parts = [] # Pointer to the part.
        query_part_stock_code = [] # Used the stock code mention for disambiguation,
                                   # it is used `None` for the "manf#".
        for part_idx, part in enumerate(parts):

            # Create a PartInfo query using the manufacturer's part number or 
            # the distributor's SKU.
            query = None
            part_dist_use_manfpn = copy.copy(DISTRIBUTORS)

            # Check if that part have stock code that is accepted to use by this module (API).
            # KiCost will prioritize these codes under "manf#" that will be used for get
            #information for the part hat were not filled with the distributor stock code. So
            # this is checked after the 'manf#' buv code.
            for d in FIELDS_CAT:
                part_stock = part.fields.get(d)
                if part_stock:
                    part_catalogue_code_dist = d[:-1]
                    if part_catalogue_code_dist in distributors_modules_dict['api_partinfo_kitspace']['distributors']:
                        part_code_dist = list({k for k, v in dist_xlate.items() if v == part_catalogue_code_dist})[0]
                        query = {'sku': {'vendor': part_code_dist, 'part': part_stock}}
                        queries.append(query)
                        query_parts.append(part)
                        query_part_stock_code.append(part_catalogue_code_dist)
                        part_dist_use_manfpn.remove(part_catalogue_code_dist)

            part_manf = part.fields.get('manf', '')
            part_code = part.fields.get('manf#')
            if part_code and not all([part.fields.get(f) for f in FIELDS_CAT]):
                query = {'mpn': {'manufacturer': part_manf, 'part': part_code}}
                queries.append(query)
                query_parts.append(part)
                query_part_stock_code.append(part_dist_use_manfpn)

        # Setup progress bar to track progress of server queries.
        progress = tqdm.tqdm(desc='Progress', total=len(query_parts), unit='part', miniters=1)

        # Slice the queries into batches of the largest allowed size and gather
        # the part data for each batch.
        for i in range(0, len(queries), MAX_PARTS_PER_QUERY):
            slc = slice(i, i+MAX_PARTS_PER_QUERY)
            get_part_info(queries[slc], query_parts[slc], query_part_stock_code[slc])
            progress.update(len(queries[slc]))

        # Restore the logging print channel now that the progress bar is no longer needed.
        logger.addHandler(logDefaultHandler)
        logger.removeHandler(logTqdmHandler)

        # Done with the scraping progress bar so delete it or else we get an
        # error when the program terminates.
        del progress
