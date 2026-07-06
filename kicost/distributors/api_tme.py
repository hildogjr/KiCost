# -*- coding: utf-8 -*-
# MIT license
#
# Copyright (C) 2022-2026 by Salvador E. Tropea / Instituto Nacional de Tecnologia Industrial
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
# https://api-doc.tme.eu/v1
# https://api-doc.tme.eu/v2 <- tokens generated after 2026-05-14
#
# Migration from v1 to v2 assisted by Gemini 3.1 Pro

# Author information.
__author__ = 'Salvador Eduardo Tropea'
__webpage__ = 'https://github.com/set-soft'
__company__ = 'Instituto Nacional de Tecnologia Industrial - Argentina'

# Libraries.
import sys
import pprint
import difflib
import collections
import json
import base64
import time
if sys.version_info[0] < 3:
    from urllib import urlencode
    from urllib2 import Request, urlopen, URLError
else:
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen
    from urllib.error import URLError

# KiCost definitions.
from .. import KiCostError, DistData, W_NOINFO, ERR_SCRAPE, W_APIFAIL
# Distributors definitions.
from .distributor import distributor_class, QueryCache, hide_secrets
from .log__ import debug_overview, debug_obsessive, debug_full, is_debug_full, warning

# Specs known by KiCost
SPEC_NAMES = {'tolerance': 'tolerance',
              'frequency': 'frequency',
              'power': 'power',
              'operating voltage': 'voltage',
              'manufacturer': 'manf',
              'temperature coefficient': 'temp_coeff'}

DIST_NAME = 'tme'
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
        self.app_secret = app_secret
        self.cache = cache
        self.access_token = None
        # Check the language
        lng = self.get_languages()
        if language not in lng:
            self.language = 'en'
            debug_overview('Language `{}` not supported using `en`'.format(language))
        debug_overview('Using `{}`'.format(self.language))
        # Check the selected country
        cnt = self.get_countries()
        country_l = country.lower()
        cnt_data = next(iter(filter(lambda x: x['id'].lower() == country_l, cnt)), None)
        if cnt_data is None:
            raise TMEError("Unsupported country `{}`".format(country))
        currencies = self.get_currencies()
        # Check if the currency is supported for this country
        if currency not in currencies:
            # Nope, use one valid
            self.currency = currencies[-1]
            debug_overview('Currency `{}` not supported for `{}` using `{}`'.format(currency, country, self.currency))
        debug_overview('Using `{}` for `{}`'.format(self.currency, cnt_data['name']))

    def _fetch_oauth_token(self):
        url = BASE_URL + '/auth/token'

        credentials = self.token + ":" + self.app_secret
        b64_creds = base64.b64encode(credentials.encode()).decode('ascii')

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic " + b64_creds
        }

        # URL encode the body payload and encode to bytes for the request
        data = do_encode(urlencode({'grant_type': 'client_credentials'}))

        debug_obsessive('Fetching TME OAuth token from {}'.format(url))
        try:
            req = Request(url, data=data, headers=headers)
            response = urlopen(req)

            # Read and decode the response
            response_body = response.read()
            if sys.version_info[0] >= 3:
                response_body = response_body.decode('utf-8')

            token_data = json.loads(response_body)
            debug_obsessive('OAuth token successfully retrieved.')
            return token_data['access_token']

        except URLError as e:
            code = getattr(e, 'code', None)
            reason = getattr(e, 'reason', str(e))
            # Attempt to read the error body for more context if available
            error_body = ""
            if hasattr(e, 'read'):
                error_body = e.read()
                if sys.version_info[0] >= 3:
                    error_body = error_body.decode('utf-8')

            raise TMEError("OAuth token request failed: `{}` ({}) - {}".format(reason, code, error_body))

    def request(self, endpoint, params):
        if self.access_token is None:
            self.access_token = self._fetch_oauth_token()

        url = BASE_URL + endpoint

        if params:
            # Using OrderedDict ensures deterministic URLs (helpful for caching/debugging)
            ordered_params = collections.OrderedDict(sorted(params.items()))
            query_string = urlencode(ordered_params)
            url += '?' + query_string

        headers = {
            "Authorization": "Bearer " + self.access_token,
            "Accept": "application/json",
            "Accept-Language": self.language
        }

        # By omitting the 'data' parameter, urllib treats this as a GET request
        return Request(url, headers=headers)

    def json_request(self, endpoint, params=None):
        if params is None:
            params = {}

        debug_obsessive('TME json request endpoint {} params {}'.format(endpoint, params))

        max_retries = 3
        for attempt in range(max_retries):
            reason = code = None
            try:
                req = self.request(endpoint, params)
                response = urlopen(req)
                break  # Success! Break out of the retry loop.

            except URLError as e:
                code = getattr(e, 'code', None)
                reason = getattr(e, 'reason', str(e))

                if code == 401:
                    # Token expired or invalid. Fetch a new one and retry.
                    debug_overview('TME API token expired (401). Refreshing token...')
                    self.access_token = self._fetch_oauth_token()
                    continue

                elif code in (403, 429):
                    # Rate limited by TME server. Wait and retry.
                    debug_obsessive('TME API rate limited ({}). Waiting 1s...'.format(code))
                    time.sleep(1)
                    continue

                else:
                    # Break immediately on other HTTP errors (e.g., 400 Bad Request)
                    raise TMEError("Server error `{}` ({}) on endpoint {}".format(reason, code, endpoint))
        else:
            # This triggers if the loop finishes without hitting `break`
            raise TMEError("Server error: Max retries ({}) exceeded for endpoint {}".format(max_retries, endpoint))

        # Parse the JSON response gracefully for Python 2 & 3
        response_body = response.read()
        if sys.version_info[0] >= 3:
            response_body = response_body.decode('utf-8')

        data = json.loads(response_body)

        # API v1 wrapped responses in a "Data" dictionary.
        # API v2 might return the structure directly. This safely handles both.
        return data.get('data', data.get('Data', data))

    def get_countries(self):
        language = self.language
        data, loaded = self.cache.load_results('all', 'countries_'+language)
        if loaded:
            debug_obsessive('Data from cache: '+pprint.pformat(data))
            v1 = data.get('CountryList')
            if v1 is not None:
                return [{"id": e.get('CountryId'), "name": e.get('Name')} for e in v1]
            return data['elements']
        data = self.json_request('/utils/countries')
        debug_obsessive('Data from web: '+pprint.pformat(data))
        self.cache.save_results('all', 'countries_'+language, data)
        return data['elements']

    def get_currencies(self):
        country = self.country
        data, loaded = self.cache.load_results(country, 'currencies')
        if loaded:
            debug_obsessive('Data from cache: '+pprint.pformat(data))
            return data['currencies']
        data = self.json_request('/utils/currencies', {'country': country})
        debug_obsessive('Data from web: '+pprint.pformat(data))
        self.cache.save_results(country, 'currencies', data)
        return data['currencies']

    def get_languages(self):
        data, loaded = self.cache.load_results('all', 'languages')
        if loaded:
            debug_obsessive('Data from cache: '+pprint.pformat(data))
            return data.get('languages', data.get('LanguageList'))
        data = self.json_request('/utils/languages')
        debug_obsessive('Data from web: '+pprint.pformat(data))
        self.cache.save_results('all', 'languages', data)
        return data['languages']

    def create_full_cache_name(self, name=''):
        return name+'_'+self.country+'_'+self.language+'_'+self.currency+'_v2'

    def get_from_cache(self, symbol):
        data, loaded = self.cache.load_results('data', self.create_full_cache_name(symbol))
        if loaded:
            debug_obsessive('Data from cache: '+pprint.pformat(data))
            return data
        return None

    def _get_products(self, symbols, endpoint, currency=False, extra_params=None):
        parameters = {'country': self.country}
        if currency:
            parameters['currency'] = self.currency
        if extra_params:
            parameters.update(extra_params)

        for c, s in enumerate(symbols):
            parameters['symbols[{}]'.format(c)] = s

        debug_obsessive(parameters)
        data = self.json_request(endpoint, parameters)
        debug_obsessive('Data from web: '+pprint.pformat(data))

        # Defensive extraction of product lists across v2 response structures
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if 'ProductList' in data:
                return data['ProductList']
            if 'elements' in data:
                return data['elements']
            if 'products' in data:
                prods = data['products']
                if isinstance(prods, list):
                    return prods
                if isinstance(prods, dict) and 'elements' in prods:
                    return prods['elements']
        return []

    def get_products(self, symbols):
        return self._get_products(symbols, '/products')

    def get_prices(self, symbols):
        # In v2 /products/data, scope[] is required to define what data to retrieve
        extra = {'scope[0]': 'prices', 'scope[1]': 'stock'}
        return self._get_products(symbols, '/products/data', currency=True, extra_params=extra)

    def get_parameters(self, symbols):
        return self._get_products(symbols, '/products/parameters')

    def get_files(self, symbols):
        return self._get_products(symbols, '/products/files')

    def get_part_info(self, missing, known):
        products = self.get_products(missing)
        prices = self.get_prices(missing)
        parameters = self.get_parameters(missing)
        files = self.get_files(missing)

        # Join all the data
        all_data = {s: {} for s in missing}
        for d in products+prices+parameters+files:
            all_data[d['symbol']].update(d)

        # Cache the data and it to the known
        qual_name = self.create_full_cache_name()
        for k, v in all_data.items():
            self.cache.save_results('data', k+qual_name, v)
            known[k] = v

    def search(self, name):
        # Try to get the data from the cache
        full_name = self.create_full_cache_name(name)
        data, loaded = self.cache.load_results('search', full_name)
        if loaded:
            debug_obsessive('Data from cache: '+pprint.pformat(data))
            return data

        # v1: The docs suggest that spaces are allowed, but replacing them is safer.
        # v2: This should avoid interpreting it as different words to search
        name = name.replace(' ', '-')

        parameters = {
            'country': self.country,
            'phrase': name,
            'scope[0]': 'products',
            'scope[1]': 'counters',
            'sort[property]': 'PRICE_FIRST_QUANTITY',
            'sort[direction]': 'asc',
            'limit': 100,   # v2 supports 100 (v1 20)
            'page': 1
        }

        data = self.json_request('/products/search', parameters)
        debug_obsessive('Data from web: '+pprint.pformat(data))

        # In v2, pagination info is under 'counters' and the list is under 'products' -> 'elements'
        total = data['counters']['count']
        product_list = data['products']['elements']

        if total > 100:
            # Get the rest of the matches
            page = 2
            while len(product_list) < total:
                parameters['page'] = page
                data = self.json_request('/products/search', parameters)
                product_list.extend(data['products']['elements'])
                page += 1

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
    env_prefix = 'TME'
    env_ops = {}

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
                        format(api_tme.enabled, hide_secrets(api_tme.token), hide_secrets(api_tme.app_secret), cache_path))
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
                docs = data.get('documents', {}).get('elements', [])
                for x in docs:
                    doc_type = x.get('type', '')
                    if doc_type in ['INS', 'DTE', 'datasheet', 'data_sheet']:
                        part.datasheet = x.get('url')
                        if part.datasheet:
                            break

            # Specifications / Parameters Mapping
            specs = {}
            params = data.get('parameters', {}).get('elements', [])
            for sp in params:
                name = sp.get('name', '')
                if not name:
                    continue
                values_list = sp.get('values', [])
                value = ", ".join([str(v.get('value', '')) for v in values_list])
                specs[name.lower()] = (name, value)
            part.update_specs(specs)

            dd = part.dd.get(DIST_NAME, DistData())

            # Stock & Ordering Mapping
            dd.moq = data.get('minimal_amount', 1)
            dd.qty_increment = data.get('multiples', 1)
            dd.qty_avail = data.get('stock_quantity', 0)
            dd.part_num = part_stock

            # URL Mapping
            dd.url = data.get('product_information_page')
            if not dd.url:
                dd.url = 'https://www.tme.eu/{}/details/{}'.format(api_tme.language, part_stock)
            if dd.url and dd.url.startswith('//'):
                dd.url = 'https:'+dd.url

            # Pricing Mapping
            dd.currency = data.get('prices', {}).get('currency', o.currency)
            price_list = data.get('prices', {}).get('elements', [])
            if price_list:
                dd.price_tiers = {p.get('amount'): p.get('price') for p in price_list}

            # Extra information
            dd.extra_info['desc'] = data.get('description', '')
            value = ''
            for spec in ('capacitance', 'resistance', 'inductance'):
                val = specs.get(spec, None)
                if val:
                    value += val[1] + ' '
            if value:
                dd.extra_info['value'] = value.strip()
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


# Ok, this is special case ... we should add others
MANF_CHANGES = {'fairchild': 'onsemi'}


def _get_manufacturer(d, unk=True):
    return d.get('manufacturer', {}).get('name', 'Unknown' if unk else '')


def _get_key(d, qty):
    """ Sorting criteria for the suggested option """
    moq = d.get('minimal_amount', 1)
    status = d.get('product_status', [])
    cannot_be_ordered = 'CANNOT_BE_ORDERED' in status
    hardly_available = 'HARDLY_AVAILABLE' in status
    return (cannot_be_ordered,  # Put first the ones in stock
            hardly_available,
            moq > qty)          # Put first the ones with a MOQ under the quantity we need


def _filter_by_manf(data, manf):
    """ Select the best matches according to the manufacturer """
    if not manf:
        return data

    manfs = {d['manufacturer']['name'].lower() for d in data if 'manufacturer' in d}
    if len(manfs) <= 1:
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
    return list(filter(lambda x: _get_manufacturer(x, unk=False).lower() == best_match, data))


def _list_comp_options(data, show, msg):
    """ Debug function used to show the list of options """
    if not show:
        return
    debug_full('  - '+msg)
    for c, d in enumerate(data):
        producer = _get_manufacturer(d)
        # v2 returns original symbols as an array 'manufacturer_symbols'
        mfg_symbols = d.get('manufacturer_symbols', [])
        orig_symbol = mfg_symbols[0] if mfg_symbols else 'N/A'

        debug_full('  {}) {} {} moq: {} status: {}'.
                   format(c+1, producer, orig_symbol, d.get('minimal_amount'), d.get('product_status')))


def _select_best(data, manf, qty):
    """ Selects the best result """
    c = len(data)
    if c == 0:
        return None
    if c == 1:
        return data[0]['symbol']

    debug_obsessive(' - Choosing the best match ({} options, qty: {} manf: {})'.format(c, qty, manf))
    ultra_debug = is_debug_full()
    _list_comp_options(data, ultra_debug, 'Original list')

    # Try to choose the best manufacturer
    data2 = _filter_by_manf(data, manf)
    if data != data2:
        producer = _get_manufacturer(data2[0])
        debug_obsessive(' - Selected manf `{}`'.format(producer))
        _list_comp_options(data2, ultra_debug, 'Manufacturer selected')
        if len(data2) == 1:
            return data2[0]['symbol']

    # Sort the results according to the best availability/price
    data3 = sorted(data2, key=lambda x: _get_key(x, qty))
    _list_comp_options(data3, ultra_debug, 'Sorted')

    return data3[0]['symbol']


distributor_class.register(api_tme, 100)
