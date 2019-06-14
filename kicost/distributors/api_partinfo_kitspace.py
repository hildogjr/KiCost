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

# Distributors definitions.
from .distributor import distributor_class

from currency_converter import CurrencyConverter
currency_convert = CurrencyConverter().convert

MAX_PARTS_PER_QUERY = 20 # Maximum number of parts in a single query.

# Information to return from PartInfo KitSpace server.

QUERY_AVAIABLE_CURRENCIES = {'GBP', 'EUR', 'USD'}
QUERY_ANSWER = '''
    mpn{manufacturer, part},
    datasheet,
    description,
    specs{key, value},
    offers{
        product_url,
        sku {vendor, part},
        description,
        moq,
        in_stock_quantity,
        prices{''' + DEFAULT_CURRENCY + '''}
        }
'''
#Informations not used: type,specs{key, name, value},image {url, credit_string, credit_url},stock_location
QUERY_ANSWER = re.sub('[\s\n]', '', QUERY_ANSWER)

QUERY_PART = 'query ($input: MpnInput!) { part(mpn: $input) {' + QUERY_ANSWER + '} }'
QUERY_MATCH = 'query ($input: [MpnOrSku]!){ match(parts: $input) {' + QUERY_ANSWER + '} }'
QUERY_SEARCH = 'query ($input: String!){ search(term: $input) {' + QUERY_ANSWER + '} }'
QUERY_URL = 'https://dev-partinfo.kitspace.org/graphql'


__all__ = ['api_partinfo_kitspace']


class api_partinfo_kitspace(distributor_class):

    @staticmethod
    def init_dist_dict():
        distributor_dict.update({
            'digikey': {
                'api_info': {'kitspace_dist_name': 'Digikey'},
                'module': 'digikey',
                'type': 'api',
                'order': {
                    'cols': ['purch', 'part_num', 'refs'],
                    'delimiter': ',', 'not_allowed_char': ',', 'replace_by_char': ';',
                },
                'label': {
                    'name': 'Digi-Key',
                    'format': {'font_color': 'white', 'bg_color': '#CC0000'}, # Digi-Key red.
                    'link': 'https://www.digikey.com/',
                },
            },
            'farnell': {
                'api_info':{'kitspace_dist_name': 'Farnell',},
                'module': 'farnell',
                'type': 'api',
                'order': {
                    'cols': ['part_num', 'purch', 'refs'],
                    'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
                },
                'label': {
                    'name': 'Farnell',
                    'format': {'font_color': 'white', 'bg_color': '#FF6600'}, # Farnell/E14 orange.
                    'link': 'https://www.newark.com/',
                },
            },
            'mouser': {
                'api_info':{'kitspace_dist_name': 'Mouser',},
                'module': 'mouser', 
                'type': 'api',
                'order': {
                    'cols': ['part_num', 'purch', 'refs'],
                    'delimiter': '|', 'not_allowed_char': '| ', 'replace_by_char': ';_',
                },
                'label': {
                    'name': 'Mouser', 
                    'format': {'font_color': 'white', 'bg_color': '#004A85'}, # Mouser blue.
                    'link': 'https://www.mouser.com',
                },
            },
            'newark': {
                'api_info':{'kitspace_dist_name': 'Newark',},
                'module': 'newark',
                'type': 'api',
                'order': {
                    'cols': ['part_num', 'purch', 'refs'],
                    'delimiter': ',', 'not_allowed_char': ',', 'replace_by_char': ';',
                },
                'label': {
                    'name': 'Newark',
                    'format': {'font_color': 'white', 'bg_color': '#A2AE06'}, # Newark/E14 olive green.
                    'link': 'https://www.newark.com/',
                },
            },
            'rs': {
                'api_info':{'kitspace_dist_name': 'RS',},
                'module': 'rs',
                'type': 'api',
                'order': {
                    'cols': ['part_num', 'purch', 'refs'],
                    'delimiter': ' ', 'not_allowed_char': ' ', 'replace_by_char': ';',
                },
                'label': {
                    'name': 'RS Components',
                    'format': {'font_color': 'white', 'bg_color': '#FF0000'}, # RS Components red.
                    'link': 'https://uk.rs-online.com/',
                },
            },
        })


    @staticmethod
    def query(query_parts, query_type=QUERY_MATCH):
        '''Send query to server and return results.'''
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
            raise Exception('Kitspace server not found.')
        elif response.status_code == requests.codes['bad_request']: #400
            raise Exception('Bad request to Kitspace server probably due to an incorrect string format.')
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

        # Translate from PartInfo distributor names to the names used internally by kicost.
        dist_xlate = {
                dist_value['api_info']['kitspace_dist_name']: dist_key
                for dist_key, dist_value in distributors.items() if dist_value['type']=='api'
            }

        def get_part_info(query, parts, currency=DEFAULT_CURRENCY):
            '''Query PartInfo for quantity/price info and place it into the parts list'''

            results = api_partinfo_kitspace.query(query)

            # Loop through the response to the query and enter info into the parts list.
            for part_query, part, result in zip(query, parts, results['data']['match']):

                if not result:
                    logger.warning('No information found for part {}'.format(str(part_query)))
                    #print('---> NO RESULT FOR', part) ##TODO

                else:

                    # Get the information of the part.
                    part.datasheet = result.get('datasheet')
                    part.lifecycle = api_partinfo_kitspace.get_value(result['specs'], 'lifecycle_status', 'active')

                    # Loop through the offers from various dists for this particular part.
                    for offer in result['offers']:
                        # Get the distributor who made the offer and add their
                        # price/qty info to the parts list if its one of the accepted distributors.
                        dist = dist_xlate.get(offer['sku']['vendor'], '')
                        if dist in distributors:

                            # Get pricing information from this distributor.
                            try:
                                price_tiers = {} # Empty dict in case of exception.
                                local_currency = list(offer['prices'].keys())
                                part.currency = local_currency[0]
                                price_tiers = {
                                    qty: float( currency_convert(price, local_currency[0], currency.upper()) )
                                    for qty, price in list(offer['prices'].values())[0]
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

                            # Use the qty increment to select the part SKU, web page, and available quantity.
                            # Do this if this is the first part offer from this dist.
                            part.part_num[dist] = offer.get('sku', '').get('part', '')
                            part.url[dist] = offer.get('product_url', '') # Page to purchase.
                            part.qty_avail[dist] = offer.get('in_stock_quantity', None) # In stock.
                            part.moq[dist] = offer.get('moq', None) # Minimum order qty.s
                            part.qty_increment[dist] = part_qty_increment

                            # Don't bother with any extra info from the distributor.
                            part.info_dist[dist] = {}

        # Get the valid distributor names used by them part catalog
        # that may be index by PartInfo. This is used to remove the
        # local distributors and future not implemented in the PartInfo
        # definition.
        distributors_name_api = [d for d in distributors if distributors[d]['type']=='api'
                            and distributors[d].get('api_info').get('kitspace_dist_name')]

        # Create queries to get part price/quantities from PartInfo.
        queries = []
        query_parts = []
        for part in parts:

            # Create a PartInfo query using the manufacturer's part number or 
            # the distributor's SKU.
            query = None
            part_code = part.fields.get('manf#')
            if part_code:
                query = {'mpn': {'manufacturer': '', 'part': part_code}}
            else:
                # No MPN, so use the first distributor SKU that's found.
                for dist_name in distributors_name_api:
                    part_code = part.fields.get(dist_name + '#')
                    if part_code:
                        query = {'sku': {'vendor': dist_name, 'part': part_code}}
                        break

            if query:
                # Add query for this part to the list of part queries.
                # part_query = {code_type: {'manufacturer': '', 'part': urlquote(part_code)}} # TODO 
                queries.append(query)
                query_parts.append(part)

        # Setup progress bar to track progress of server queries.
        progress = tqdm.tqdm(desc='Progress', total=len(query_parts), unit='part', miniters=1)

        # Slice the queries into batches of the largest allowed size and gather
        # the part data for each batch.
        for i in range(0, len(queries), MAX_PARTS_PER_QUERY):
            slc = slice(i, i+MAX_PARTS_PER_QUERY)
            query_batch = queries[slc]
            part_batch = query_parts[slc]
            get_part_info(query_batch, part_batch)
            progress.update(len(query_batch))

        # Restore the logging print channel now that the progress bar is no longer needed.
        logger.addHandler(logDefaultHandler)
        logger.removeHandler(logTqdmHandler)

        # Done with the scraping progress bar so delete it or else we get an
        # error when the program terminates.
        del progress
