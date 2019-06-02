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
from urllib.parse import quote_plus as urlquote

# KiCost definitions.
from .global_vars import * # Debug information, `distributor_dict` and `SEPRTR`.

# Distributors definitions.
from .distributor import distributor_class

from currency_converter import CurrencyConverter
currency_convert = CurrencyConverter().convert

MAX_PARTS_BY_QUERY = 20 # Maximum part list length to one single query.

# Information to return from PartInfo KitSpace server.

QUERY_AVAIABLE_CURRENCIES = {'GBP', 'EUR', 'USD'}
QUERY_ANSWER = '''
    mpn{manufacturer, part},
    type,
    datasheet,
    description,
    image{url, credit_string, credit_url},
    specs{key, name, value},
    offers{
        sku {vendor, part},
        description,
        moq,
        in_stock_quantity,
        stock_location,
        image {url, credit_string, credit_url},
        specs {key, name, value},
        prices{USD}
        }
'''
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


    def query(query_parts, query_type=QUERY_MATCH):
        '''Send query to server and return results.'''
        #r = requests.post(QUERY_URL, {"query": QUERY_SEARCH, "variables": variables}) #TODO future use for ISSUE #17
        variables = re.sub('\'', '\"', str(query_parts))
        variables = re.sub('\s', '', variables)
        variables = '{{"input":{}}}'.format(variables)
        response = requests.post(QUERY_URL, {'query': query_type, "variables": variables})
        if response.status_code == requests.codes['ok']: #200
            results = json.loads(response.text)
            return results
        elif response.status_code == requests.codes['not_found']: #404
            raise Exception('Kitspace server not found.')
        elif response.status_code == requests.codes['bad_request']: #400
            raise Exception('Bad request to Kitspace server probably due uncorrect strig format.')
        else:
            raise Exception('Kitspace error: ' + str(response.status_code))

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

    def query_part_info(parts, distributors, currency='USD'):
        '''Fill-in the parts with price/qty/etc info from KitSpace.'''
        logger.log(DEBUG_OVERVIEW, '# Getting part data from KitSpace...')

        # Setup progress bar to track progress of server queries.
        progress = tqdm.tqdm(desc='Progress', total=len(parts), unit='part', miniters=1)

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

        def get_part_info(query, parts, index, currency='USD'):
            '''Query PartInfo for quantity/price info and place it into the parts list'''

            results = api_partinfo_kitspace.query(query)

            # Loop through the response to the query and enter info into the parts list.
            for i in range(len(index)):
                result = results['data']['match'][i]
                idx = index[i]

                parts[idx].price_tiers = {}
                parts[idx].part_num = {}
                parts[idx].url = {}
                parts[idx].qty_avail = {}
                parts[idx].moq = {}
                parts[idx].qty_increment = {}
                parts[idx].info_dist = {}
                parts[idx].currency = 'USD'
                if not result:
                    #logger.warning('Found any result to part \'{}\''.format(parts[idx].get('manf#')))
                    print('---> NOT GET RESULT',idx, result) ##TODO
                else:

                    # Get the information of the part.
                    parts[idx].datasheet = result.get('datasheet')
                    parts[idx].lifecycle = api_partinfo_kitspace.get_value(result['specs'], 'lifecycle_status', 'active')

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
                                parts[idx].currency = local_currency[0]
                                price_tiers = {
                                    qty: float( currency_convert(price, local_currency[0], currency.upper()) )
                                    for qty, price in list(offer['prices'].values())[0]
                                    }
                                # Combine price lists for multiple offers from the same distributor
                                # to build a complete list of cut-tape and reeled components.
                                if not dist in parts[idx].price_tiers:
                                    parts[idx].price_tiers[dist] = {}
                                parts[idx].price_tiers[dist].update(price_tiers)
                            except Exception:
                                pass  # Price list is probably missing so leave empty default dict in place.

                            # Compute the quantity increment between the lowest two prices.
                            # This will be used to distinguish the cut-tape from the reeled components.
                            try:
                                part_break_qtys = sorted(price_tiers.keys())
                                part_qty_increment = part_break_qtys[1] - part_break_qtys[0]
                            except Exception:
                                # This will happen if there are not enough entries in the price/qty list.
                                # As a stop-gap measure, just assign infinity to the part increment.
                                # A better alternative may be to examine the packaging field of the offer.
                                part_qty_increment = float("inf")

                            # Use the qty increment to select the part SKU, web page, and available quantity.
                            # Do this if this is the first part offer from this dist.
                            parts[idx].part_num[dist] = offer.get('sku', '').get('part', '')
                            parts[idx].url[dist] = offer.get('product_url', '') # Page to purchase.
                            parts[idx].qty_avail[dist] = offer.get('in_stock_quantity', None) # In stock.
                            parts[idx].moq[dist] = offer.get('moq', None) # Minimum order qty.s
                            parts[idx].qty_increment[dist] = part_qty_increment

                            # Don't bother with any extra info from the distributor.
                            parts[idx].info_dist[dist] = {}
                            print(idx, '----',dist,parts[idx].part_num[dist],parts[idx].price_tiers[dist])
                            

        # Get the valid distributors names used by them part catalog
        # that may be index by PartInfo. This is used to remove the
        # local distributors and future not implemented in the PartInfo
        # definition.
        distributors_name_api = [d for d in distributors if distributors[d]['type']=='api'
                            and distributors[d].get('api_info').get('kitspace_dist_name')]

        # Break list of parts into smaller pieces and get price/quantities from PartInfo.
        partinfo_query = []
        part_enumerate = []
        prev_idx = 0 # Used to record index where parts query occurs.
        for idx, part in enumerate(parts):

            # Create an PartInfo query using the manufacturer's part number or 
            # distributor SKU.
            manf_code = part.fields.get('manf#')
            if manf_code:
                #part_query = {'mpn': {'manufacturer': '', 'part': urlquote(manf_code)} }#TODO
                part_query = {'mpn': {'manufacturer': '', 'part': manf_code} }
            else:
                try:
                    # No MPN, so use the first distributor SKU that's found.
                    #skus = [part.fields.get(d + '#', '') for d in `distributors_name_api`
                    #            if part.fields.get(d + '#') ]
                    for api_dist_sku in distributors_name_api:
                        sku = part.fields.get(api_dist_sku + '#', '')
                        if sku:
                            break
                    # Create the part query using SKU matching.
                    if sku:
                        part_query = {'sku': {'manufacturer': '', 'part': sku} }
                        # Because was used the distributor (enrolled at Octopart list)
                        # despite the normal 'manf#' code, take the sub quantity as
                        # general sub quantity of the current part.
                        try:
                            part.fields['manf#_qty'] = part.fields[api_dist_sku + '#_qty']
                            logger.warning("Associated {q} quantity to '{r}' due \"{f}#={q}:{c}\".".format(
                                    q=part.fields[api_dist_sku + '#_qty'], r=part.refs,
                                    f=api_dist_sku, c=part.fields[api_dist_sku+'#']))
                        except:
                            pass
                except IndexError:
                    # No MPN or SKU, so skip this part.
                    continue

            # Add query for this part to the list of part queries.
            partinfo_query.append(part_query)
            part_enumerate.append(idx)

            # Once there are enough (but not too many) part queries, make a query request to Octopart.
            if len(partinfo_query) == MAX_PARTS_BY_QUERY:
                get_part_info(partinfo_query, parts, part_enumerate)
                progress.update(idx - prev_idx) # Update progress bar.
                prev_idx = idx;
                partinfo_query = []  # Get ready for next batch.
                part_enumerate = []

        # Query PartInfo for the last batch of parts.
        if partinfo_query:
            get_part_info(partinfo_query, parts, part_enumerate)
            progress.update(len(parts)-prev_idx) # This will indicate final progress of 100%.

        # Restore the logging print channel now that the progress bar is no longer needed.
        logger.addHandler(logDefaultHandler)
        logger.removeHandler(logTqdmHandler)

        # Done with the scraping progress bar so delete it or else we get an
        # error when the program terminates.
        del progress
