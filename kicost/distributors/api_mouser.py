# -*- coding: utf-8 -*-
# MIT license
#
# Copyright (c) 2021 SPARK Microsystems
# Copyright (c) 2021 by Salvador E. Tropea / Instituto Nacional de Tecnologia Industrial
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
# Most of the API code comes from https://github.com/sparkmicro/mouser-api

# Author information.
__author__ = 'Salvador Eduardo Tropea'
__webpage__ = 'https://github.com/set-soft'
__company__ = 'Instituto Nacional de Tecnologia Industrial - Argentina'

# Libraries.
import os
import pprint
import json
import requests
import re

# KiCost definitions.
from ..global_vars import DEBUG_OVERVIEW, DEBUG_OBSESSIVE, DEBUG_DETAILED, W_NOINFO, W_APIFAIL, KiCostError, ERR_SCRAPE
from .. import DistData
# Distributors definitions.
from .distributor import distributor_class, QueryCache

available = True

DIST_NAME = 'mouser'
ENV_OPS = {'MOUSER_PART_API_KEY': 'key',
           'MOUSER_CACHE_TTL': 'cache_ttl'}
# Mouser Base URL
BASE_URL = 'https://api.mouser.com/api/v1.0'

__all__ = ['api_mouser']


class MouserError(Exception):
    pass


def get_number(string):
    index = next((i for i, d in enumerate(string) if d.isdigit()), None)
    if index is None:
        raise MouserError('Malformed price: ' + string)
    return float(string[index:])


# ####################################
# Base classes
# ####################################


class MouserAPIRequest:
    """ Mouser API Request """

    url = None
    api_url = None
    method = None
    body = {}
    response = None
    api_key = None

    def __init__(self, url, method, key, *args):
        if not url or not method:
            return None
        self.api_url = BASE_URL + url
        self.method = method

        # Append argument
        if len(args) == 1:
            self.api_url += '/' + str(args[0])

        # Append API Key
        self.api_key = key

        if self.api_key:
            self.url = self.api_url + '?apiKey=' + self.api_key

    def get(self, url):
        response = requests.get(url=url)
        return response

    def post(self, url, body):
        headers = {
            'Content-Type': 'application/json',
        }
        response = requests.post(url=url, data=json.dumps(body), headers=headers)
        return response

    def run(self, body={}):
        if self.method == 'GET':
            self.response = self.get(self.url)
        elif self.method == 'POST':
            self.response = self.post(self.url, body)
        if self.response:
            self.response_parsed = self.get_response()
        else:
            self.response_parsed = None

        return True if self.response else False

    def get_response(self):
        if self.response is not None:
            try:
                return json.loads(self.response.text)
            except json.decoder.JSONDecodeError:
                return self.response.text

        return {}

    def __str__(self):
        if self.response_parsed is None:
            return 'None'
        return json.dumps(self.response_parsed, indent=4, sort_keys=True)


class MouserBaseRequest(MouserAPIRequest):
    """ Mouser Base Request """

    name = ''
    allowed_methods = ['GET', 'POST']
    operation = None
    operations = {}

    def __init__(self, operation, key, *args):
        ''' Init '''
        if operation not in self.operations:
            msg = '[{}] Invalid Operation'.format(self.name)
            valid_operations = [operation for operation, values in self.operations.items() if values[0] and values[1]]
            if valid_operations:
                msg += ' Valid operations: ' + str(valid_operations)
            raise MouserError(msg)
            return

        self.operation = operation
        (method, url) = self.operations.get(self.operation, ('', ''))
        if not url or not method or method not in self.allowed_methods:
            raise MouserError('[{}]\tOperation "{}" Not Yet Supported'.format(self.name, operation))
            return
        super().__init__(url, method, key, *args)


# ####################################
# Part Search
# ####################################

class MouserPartSearchRequest(MouserBaseRequest):
    """ Mouser Part Search Request """

    name = 'Part Search'
    operations = {
        'keyword': ('', ''),
        'keywordandmanufacturer': ('', ''),
        'partnumber': ('POST', '/search/partnumber'),
        'partnumberandmanufacturer': ('', ''),
        'manufacturerlist': ('', ''),
    }

    def get_clean_response(self):
        cleaned_data = {
            'Availability': '',
            'Category': '',
            'DataSheetUrl': '',
            'Description': '',
            'ImagePath': '',
            'LifecycleStatus': '',
            'Manufacturer': '',
            'ManufacturerPartNumber': '',
            'Min': '',
            'MouserPartNumber': '',
            'ProductDetailUrl': '',
            'ProductAttributes': [],
            'PriceBreaks': [],
        }

        response = self.response_parsed
        if not response:
            return None
        try:
            parts = response['SearchResults'].get('Parts', [])
        except AttributeError:
            return None

        if not parts:
            return None
        # Process first part
        part_data = parts[0]
        # Merge
        for key in cleaned_data:
            cleaned_data[key] = part_data[key]
        return cleaned_data

    def print_clean_response(self):
        response_data = self.get_clean_response()
        print(json.dumps(response_data, indent=4, sort_keys=True))

    def get_body(self, **kwargs):
        body = {}
        if self.operation == 'partnumber':
            part_number = kwargs.get('part_number', None)
            option = kwargs.get('option', 'None')

            if part_number:
                body = {
                    'SearchByPartRequest': {
                        'mouserPartNumber': part_number,
                        'partSearchOptions': option,
                    }
                }
        return body

    def part_search(self, part_number, option='None'):
        '''Mouser Part Number Search '''
        kwargs = {
            'part_number': part_number,
            'option': option,
        }
        self.body = self.get_body(**kwargs)
        if self.api_key:
            res = self.run(self.body)
            if res and self.response_parsed is not None:
                errors = self.response_parsed.get('Errors', None)
                if errors is not None and len(errors) >= 1:
                    error = errors[0]
                    raise MouserError(error['Message'] + ' (' + error['Code'] + ' ' + error['PropertyName'] + ')')
            return res
        else:
            return False


class api_mouser(distributor_class):
    name = 'Mouser'
    type = 'api'
    enabled = True
    url = 'https://api.mouser.com/'  # Web site API information.
    api_distributors = [DIST_NAME]
    # Options supported by this API
    config_options = {'key': str}
    key = None
    cache = None

    @staticmethod
    def configure(ops):
        cache_ttl = 7
        cache_path = None
        for k, v in ops.items():
            if k == 'key':
                api_mouser.key = v
            elif k == 'enable':
                api_mouser.enabled = v
            elif k == 'cache_ttl':
                cache_ttl = v
            elif k == 'cache_path':
                cache_path = v
        if api_mouser.enabled and api_mouser.key is None:
            distributor_class.logger.warning(W_APIFAIL+"Can't enable Mouser without a `key`")
            api_mouser.enabled = False
        distributor_class.logger.log(DEBUG_OBSESSIVE, 'Mouser API configured to enabled {} key {} path {}'.
                                     format(api_mouser.enabled, api_mouser.key, cache_path))
        if not api_mouser.enabled:
            return
        # Try to configure the plug-in
        api_mouser.cache = QueryCache(cache_path, cache_ttl)

    @staticmethod
    def _query_part_info(parts, distributors, currency):
        '''Fill-in the parts with price/qty/etc info from KitSpace.'''
        if DIST_NAME not in distributors:
            distributor_class.logger.log(DEBUG_OVERVIEW, '# Skipping Mouser plug-in')
            return
        distributor_class.logger.log(DEBUG_OVERVIEW, '# Getting part data from Mouser...')
        field_cat = DIST_NAME + '#'
        in_stock_re = re.compile(r'(\d+) in stock', re.I)

        # Setup progress bar to track progress of server queries.
        progress = distributor_class.progress(len(parts), distributor_class.logger)
        for part in parts:
            partnumber = None
            data = None
            # Get the Mouser P/N for this part
            part_stock = part.fields.get(field_cat)
            if part_stock:
                partnumber = part_stock
                prefix = 'mou'
            else:
                # No Mouser P/N, search using the manufacturer code
                partnumber = part.fields.get('manf#')
                prefix = 'mpn'
            if partnumber:
                distributor_class.logger.log(DEBUG_DETAILED, 'P/N: ' + partnumber)
                request, loaded = api_mouser.cache.load_results(prefix, partnumber)
                if loaded:
                    data = request.get_clean_response()
                else:
                    request = MouserPartSearchRequest('partnumber', api_mouser.key)
                    if request.part_search(partnumber):
                        data = request.get_clean_response()
                        api_mouser.cache.save_results(prefix, partnumber, request)

            if data is None:
                distributor_class.logger.warning(W_NOINFO+'No information found at Mouser for part/s \'{}\''.format(part.refs))
            else:
                distributor_class.logger.log(DEBUG_OBSESSIVE, '* Part info before adding data:')
                distributor_class.logger.log(DEBUG_OBSESSIVE, pprint.pformat(part.__dict__))
                distributor_class.logger.log(DEBUG_OBSESSIVE, '* Data found:')
                distributor_class.logger.log(DEBUG_OBSESSIVE, str(request))
                if not part.datasheet:
                    datasheet = data['DataSheetUrl']
                    if datasheet:
                        part.datasheet = datasheet
                if not part.lifecycle:
                    lifecycle = data['LifecycleStatus']
                    if lifecycle:
                        part.lifecycle = lifecycle.lower()
                dd = part.dd.get(DIST_NAME, DistData())
                dd.qty_increment = dd.moq = int(data['Min'])
                dd.url = data['ProductDetailUrl']
                dd.part_num = data['MouserPartNumber']
                dd.qty_avail = 0
                res_stock = in_stock_re.match(data['Availability'])
                if res_stock:
                    dd.qty_avail = int(res_stock.group(1))
                pb = data['PriceBreaks']
                dd.currency = pb[0]['Currency']
                dd.price_tiers = {p['Quantity']: get_number(p['Price']) for p in pb}
                # Extra information
                product_description = data['Description']
                if product_description:
                    dd.extra_info['desc'] = product_description
                part.dd[DIST_NAME] = dd
                distributor_class.logger.log(DEBUG_OBSESSIVE, '* Part info after adding data:')
                distributor_class.logger.log(DEBUG_OBSESSIVE, pprint.pformat(part.__dict__))
                distributor_class.logger.log(DEBUG_OBSESSIVE, pprint.pformat(dd.__dict__))
            progress.update(1)
        progress.close()

    @staticmethod
    def query_part_info(parts, distributors, currency):
        msg = None
        try:
            api_mouser._query_part_info(parts, distributors, currency)
        except MouserError as e:
            msg = e.args[0]
        if msg is not None:
            raise KiCostError(msg, ERR_SCRAPE)
        return set([DIST_NAME])

    @staticmethod
    def from_environment(options, overwrite):
        ''' Configuration from the environment. '''
        # Configure the module from the environment
        # The command line will overwrite it using set_options()
        for k, v in ENV_OPS.items():
            api_mouser._set_from_env(v, os.getenv(k), options, overwrite, api_mouser.config_options)


distributor_class.register(api_mouser, 100)
