# -*- coding: utf-8 -*-
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
# I took the basic query from https://github.com/krzych82/api-client-python3.git

# Author information.
__author__ = 'Salvador Eduardo Tropea'
__webpage__ = 'https://github.com/set-soft'
__company__ = 'Instituto Nacional de Tecnologia Industrial - Argentina'

# Libraries.
import os
import sys
import pprint
import difflib
import collections
import json
import base64
import hmac
import hashlib
if sys.version_info[0] < 3:
    from urllib import quote, urlencode
    from urllib2 import Request, urlopen, URLError
else:
    from urllib.parse import quote, urlencode
    from urllib.request import Request, urlopen
    from urllib.error import URLError

# KiCost definitions.
from .. import KiCostError, DistData, W_NOINFO, ERR_SCRAPE, W_APIFAIL
# Distributors definitions.
from .distributor import distributor_class, QueryCache
from .log__ import debug_overview, debug_obsessive, debug_full, is_debug_full, warning

# Specs known by KiCost
SPEC_NAMES = {'tolerance': 'tolerance',
              'frequency': 'frequency',
              'power': 'power',
              'operating voltage': 'voltage',
              'manufacturer': 'manf',
              'temperature coefficient': 'temp_coeff'}

DIST_NAME = 'tme'
ENV_OPS = {'TME_TOKEN': 'token',
           'TME_APP_SECRET': 'app_secret',
           'TME_CACHE_TTL': 'cache_ttl'}

BASE_URL = 'https://api.tme.eu'
MAX_PARTS_PER_QUERY = 10

__all__ = ['api_tme']


def do_encode(string):
    if sys.version_info[0] < 3:
        return string
    return string.encode()


class TMEError(Exception):
    pass


class TME(object):
    def __init__(self, country, language, app_secret, token, cache, currency):
        # Adapt to what TME uses
        currency = currency.upper()
        country = country.upper()
        language = language.lower()
        # Store the options in the object
        self.currency = currency
        self.country = country
        self.language = language
        self.token = token
        self.app_secret = do_encode(app_secret)
        self.cache = cache
        # Check the language
        lng = self.get_languages()
        if language not in lng:
            self.language = 'EN'
            debug_overview('Language `{}` not supported using `EN`'.format(language))
        debug_overview('Using `{}`'.format(self.language))
        # Check the selected country
        cnt = self.get_countries()
        country_l = country.lower()
        cnt_data = next(iter(filter(lambda x: x['CountryId'].lower() == country_l, cnt)), None)
        if cnt_data is None:
            raise TMEError("Unsupported country `{}`".format(country))
        # Check if the currency is supported for this country
        if currency not in cnt_data['CurrencyList']:
            # Nope, use the default for this country
            self.currency = cnt_data['Currency']
            debug_overview('Currency `{}` not supported for `{}` using `{}`'.format(currency, country, self.currency))
        debug_overview('Using `{}` for `{}`'.format(self.currency, cnt_data['Name']))

    def _get_signature_base(self, url, params):
        params = collections.OrderedDict(sorted(params.items()))
        encoded_params = urlencode(params)
        signature_base = 'POST'+'&'+quote(url, '')+'&'+quote(encoded_params, '')
        return do_encode(signature_base)

    def _calculate_signature(self, url, params):
        hmac_value = hmac.new(self.app_secret, self._get_signature_base(url, params), hashlib.sha1).digest()
        return base64.encodebytes(hmac_value).rstrip()

    def request(self, endpoint, params, format='json'):
        url = BASE_URL+endpoint+'.'+format
        params['Token'] = self.token
        params['ApiSignature'] = self._calculate_signature(url, params)
        data = do_encode(urlencode(params))
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        return Request(url, data, headers)

    def json_request(self, endpoint, params={}):
        reason = code = None
        debug_obsessive('TME json request endpoint {} params {}'.format(endpoint, params))
        try:
            response = urlopen(self.request(endpoint, params))
        except URLError as e:
            reason = e.reason
            code = e.code
        if reason:
            raise TMEError("Server error `{}` ({})".format(reason, code))
        data = json.loads(response.read())
        return data['Data']

    def get_countries(self):
        language = self.language
        data, loaded = self.cache.load_results('all', 'countries_'+language)
        if loaded:
            debug_obsessive('Data from cache: '+pprint.pformat(data))
            return data['CountryList']
        data = self.json_request('/Utils/GetCountries', {'Language': language})
        debug_obsessive('Data from web: '+pprint.pformat(data))
        self.cache.save_results('all', 'countries_'+language, data)
        return data['CountryList']

    def get_languages(self):
        data, loaded = self.cache.load_results('all', 'languages')
        if loaded:
            debug_obsessive('Data from cache: '+pprint.pformat(data))
            return data['LanguageList']
        data = self.json_request('/Utils/GetLanguages')
        debug_obsessive('Data from web: '+pprint.pformat(data))
        self.cache.save_results('all', 'languages', data)
        return data['LanguageList']

    def get_from_cache(self, symbol):
        full_name = symbol+'_'+self.country+'_'+self.language+'_'+self.currency
        data, loaded = self.cache.load_results('data', full_name)
        if loaded:
            debug_obsessive('Data from cache: '+pprint.pformat(data))
            return data
        return None

    def _get_products(self, symbols, kind, currency=False):
        parameters = {'Country': self.country,
                      'Language': self.language}
        if currency:
            parameters['Currency'] = self.currency
        for c, s in enumerate(symbols):
            parameters['SymbolList[{}]'.format(c)] = s
        debug_obsessive(parameters)
        data = self.json_request('/Products/'+kind, parameters)
        debug_obsessive('Data from web: '+pprint.pformat(data))
        return data['ProductList']

    def get_products(self, symbols):
        return self._get_products(symbols, 'GetProducts')

    def get_prices(self, symbols):
        return self._get_products(symbols, 'GetPricesAndStocks', currency=True)

    def get_parameters(self, symbols):
        return self._get_products(symbols, 'GetParameters')

    def get_files(self, symbols):
        return self._get_products(symbols, 'GetProductsFiles')

    def get_part_info(self, missing, known):
        products = self.get_products(missing)
        prices = self.get_prices(missing)
        parameters = self.get_parameters(missing)
        files = self.get_files(missing)
        # Join all the data
        all_data = {s: {} for s in missing}
        for d in products+prices+parameters+files:
            all_data[d['Symbol']].update(d)
        # Cache the data and it to the known
        qual_name = '_'+self.country+'_'+self.language+'_'+self.currency
        for k, v in all_data.items():
            self.cache.save_results('data', k+qual_name, v)
            known[k] = v

    def search(self, name):
        # Try to get the data from the cache
        full_name = name+'_'+self.country+'_'+self.language+'_'+self.currency
        data, loaded = self.cache.load_results('search', full_name)
        if loaded:
            debug_obsessive('Data from cache: '+pprint.pformat(data))
            return data
        # The docs suggest that spaces are allowed, but I get 400 (Bad Request)
        name = name.replace(' ', '-')
        parameters = {'Country': self.country,
                      'Language': self.language,
                      'SearchPlain': name,
                      'SearchOrder': 'PRICE_FIRST_QUANTITY',
                      'SearchOrderType': 'ASC'}
        data = self.json_request('/Products/Search', parameters)
        debug_obsessive('Data from web: '+pprint.pformat(data))
        total = data['Amount']
        if total > 20:
            # Get the rest of the matches
            product_list = data['ProductList']
            page = 2
            while len(product_list) < total:
                parameters = {'Country': self.country,
                              'Language': self.language,
                              'SearchPlain': name,
                              'SearchOrder': 'PRICE_FIRST_QUANTITY',
                              'SearchOrderType': 'ASC',
                              'SearchPage': str(page)}
                data = self.json_request('/Products/Search', parameters)
                product_list.extend(data['ProductList'])
                page = page+1
        else:
            product_list = data['ProductList']
        self.cache.save_results('search', full_name, product_list)
        return product_list


class api_tme(distributor_class):
    name = 'TME'
    type = 'api'
    # Currently enabled only by request
    enabled = True

    url = 'https://developers.tme.eu/en/'  # Web site API information.
    api_distributors = [DIST_NAME]
    # Options supported by this API
    config_options = {'token': str,
                      'app_secret': str,
                      'country': str,
                      'language': str}
    token = None
    app_secret = None
    country = 'US'
    language = 'EN'

    @staticmethod
    def configure(ops):
        cache_ttl = 7
        cache_path = None
        for k, v in ops.items():
            if k == 'token':
                api_tme.token = v
            elif k == 'app_secret':
                api_tme.app_secret = v
            elif k == 'country':
                api_tme.country = v
            elif k == 'language':
                api_tme.language = v
            elif k == 'enable':
                api_tme.enabled = v
            elif k == 'cache_ttl':
                cache_ttl = v
            elif k == 'cache_path':
                cache_path = v
        if api_tme.enabled and (api_tme.token is None or api_tme.app_secret is None):
            warning(W_APIFAIL, "Can't enable TME without a `token` and an `app_secret`")
            api_tme.enabled = False
        debug_obsessive('TME API configured to enabled {} token {} app_secret {} path {}'.
                        format(api_tme.enabled, api_tme.token, api_tme.app_secret, cache_path))
        if not api_tme.enabled:
            return
        # Configure the cache
        api_tme.cache = QueryCache(cache_path, cache_ttl)

    @staticmethod
    def _query_part_info(parts, distributors, currency):
        '''Fill-in the parts with price/qty/etc info from KitSpace.'''
        debug_overview('# Getting part data from TME ...')
        field_cat = DIST_NAME + '#'
        o = TME(api_tme.country, api_tme.language, api_tme.app_secret, api_tme.token, api_tme.cache, currency)
        #
        # First pass: collect the missing TME part numbers
        #
        # Setup progress bar to track progress of server queries.
        progress = distributor_class.progress(len(parts), distributor_class.logger)
        symbols = collections.OrderedDict()
        missing_symbols = []
        for part in parts:
            # Get the TME P/N for this part
            part_stock = part.fields.get(field_cat)
            if not part_stock:
                # We can't get information without a valid TME code (symbol)
                part_manf = part.fields.get('manf', '')
                part_code = part.fields.get('manf#')
                if part_code:
                    debug_obsessive('Searching P/N: {} from {}'.format(part_code, part_manf))
                    candidates = o.search(part_code)
                    debug_obsessive('Found {} matches'.format(len(candidates)))
                    part_stock = part.fields[field_cat] = _select_best(candidates, part_manf, part.qty_total_spreadsheet)
            if part_stock:
                # Add this symbol to the list of needed
                data = o.get_from_cache(part_stock)
                symbols[part_stock] = data
                if data is None:
                    missing_symbols.append(part_stock)
            progress.update(1)
        progress.close()
        #
        # Second pass: collect the missing data
        #
        if missing_symbols:
            n_unsolved = len(missing_symbols)
            progress = distributor_class.progress(n_unsolved, distributor_class.logger)
            for i in range(0, n_unsolved, MAX_PARTS_PER_QUERY):
                slc = slice(i, i+MAX_PARTS_PER_QUERY)
                o.get_part_info(missing_symbols[slc], symbols)
                progress.update(len(missing_symbols[slc]))
            progress.close()
        #
        # Fill the part information
        #
        for part in parts:
            part_stock = part.fields.get(field_cat)
            if not part_stock:
                warning(W_NOINFO, 'No information found at TME for part/s \'{}\''.format(part.refs))
                continue
            data = symbols[part_stock]
            debug_obsessive('* Part info before adding data:')
            debug_obsessive(pprint.pformat(part.__dict__))
            debug_obsessive('* Data found:')
            debug_obsessive(pprint.pformat(data))
            if part.datasheet is None:
                ds = next(iter(filter(lambda x: x['DocumentType'] in ['INS', 'DTE'], data['Files']['DocumentList'])), None)
                if ds:
                    part.datasheet = ds['DocumentUrl']
            specs = {}
            for sp in data.get('ParameterList', []):
                name = sp['ParameterName']
                name_l = name.lower()
                value = sp['ParameterValue']
                specs[name_l] = (name, value)
            part.update_specs(specs)
            dd = part.dd.get(DIST_NAME, DistData())
            dd.moq = data['MinAmount']
            dd.qty_increment = data['Multiples']
            dd.url = data['ProductInformationPage']
            dd.part_num = part_stock
            dd.qty_avail = data['Amount']
            dd.currency = o.currency
            prices = data.get('PriceList', None)
            if prices:
                dd.price_tiers = {p['Amount']: p['PriceValue'] for p in prices}
            # Extra information
            dd.extra_info['desc'] = data['Description']
            value = ''
            for spec in ('capacitance', 'resistance', 'inductance'):
                val = specs.get(spec, None)
                if val:
                    value += val[1] + ' '
            if value:
                dd.extra_info['value'] = value
            for spec, name in SPEC_NAMES.items():
                val = specs.get(spec, None)
                if val:
                    dd.extra_info[name] = val[1]
            part.dd[DIST_NAME] = dd
            debug_obsessive('* Part info after adding data:')
            debug_obsessive(pprint.pformat(part.__dict__))
            # debug_obsessive(pprint.pformat(dd.__dict__))

    @staticmethod
    def query_part_info(parts, distributors, currency):
        msg = None
        try:
            api_tme._query_part_info(parts, distributors, currency)
        except TMEError as e:
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
            api_tme._set_from_env(v, os.getenv(k), options, overwrite, api_tme.config_options)


# Ok, this is special case ... we should add others
MANF_CHANGES = {'fairchild': 'onsemi'}


def _get_key(d, qty):
    """ Sorting criteria for the suggested option """
    moq = d['MinAmount']
    status = d['ProductStatusList']
    cannot_be_ordered = 'CANNOT_BE_ORDERED' in status
    hardly_available = 'HARDLY_AVAILABLE' in status
    return (cannot_be_ordered,  # Put first the ones in stock
            hardly_available,
            moq > qty)          # Put first the ones with a MOQ under the quantity we need


def _filter_by_manf(data, manf):
    """ Select the best matches according to the manufacturer """
    if not manf:
        return data
    manfs = {d['Producer'].lower() for d in data}
    if len(manfs) == 1:
        return data
    manf = manf.lower()
    best_matches = difflib.get_close_matches(manf, manfs)
    if len(best_matches) == 0:
        new_name = None
        for k, v in MANF_CHANGES.items():
            if k in manf:
                new_name = v
                break
        if new_name:
            best_matches = difflib.get_close_matches(new_name, manfs)
        if len(best_matches) == 0:
            return data
    best_match = best_matches[0]
    return list(filter(lambda x: x['Producer'].lower() == best_match, data))


def _list_comp_options(data, show, msg):
    """ Debug function used to show the list of options """
    if not show:
        return
    debug_full('  - '+msg)
    for c, d in enumerate(data):
        debug_full('  {}) {} {} moq: {} status: {}'.
                   format(c+1, d['Producer'], d['OriginalSymbol'], d['MinAmount'], d['ProductStatusList']))


def _select_best(data, manf, qty):
    """ Selects the best result """
    c = len(data)
    if c == 0:
        return None
    if c == 1:
        return data[0]['Symbol']
    debug_obsessive(' - Choosing the best match ({} options, qty: {} manf: {})'.format(c, qty, manf))
    ultra_debug = is_debug_full()
    _list_comp_options(data, ultra_debug, 'Original list')
    # Try to choose the best manufacturer
    data2 = _filter_by_manf(data, manf)
    if data != data2:
        debug_obsessive(' - Selected manf `{}`'.format(data2[0]['Producer']))
        _list_comp_options(data2, ultra_debug, 'Manufacturer selected')
        if len(data2) == 1:
            return data2[0]['Symbol']
    # Sort the results according to the best availability/price
    data3 = sorted(data2, key=lambda x: _get_key(x, qty))
    _list_comp_options(data3, ultra_debug, 'Sorted')
    return data3[0]['Symbol']


distributor_class.register(api_tme, 100)
