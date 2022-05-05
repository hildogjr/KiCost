# -*- coding: utf-8 -*-
# MIT license
#
# Copyright (C) 2021 by Salvador E. Tropea / Instituto Nacional de Tecnologia Industrial
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
__author__ = 'Salvador Eduardo Tropea'
__webpage__ = 'https://github.com/set-soft'
__company__ = 'Instituto Nacional de Tecnologia Industrial - Argentina'

# Libraries.
import os
import pprint
import requests
import difflib

# KiCost definitions.
from .. import KiCostError, DistData, W_NOINFO, ERR_SCRAPE, W_APIFAIL, W_AMBIPN
# Distributors definitions.
from .distributor import distributor_class, QueryCache
from .log__ import debug_detailed, debug_overview, debug_obsessive, debug_full, warning, is_debug_full

# Countries supported by Farnell (*.farnell.com)
FARNELL_SUP = {'bg': 'EUR',
               'cz': 'CZK',
               'dk': 'DKK',
               'at': 'EUR',
               'ch': 'CHF',
               'de': 'EUR',
               'ie': 'EUR',
               'il': 'USD',
               'uk': 'GBP',
               'es': 'EUR',
               'ee': 'EUR',
               'fi': 'EUR',
               'fr': 'EUR',
               'hu': 'HUF',
               'it': 'EUR',
               'lt': 'EUR',
               'lv': 'EUR',
               'be': 'EUR',
               'nl': 'EUR',
               'no': 'NOK',
               'pl': 'PLN',
               'pt': 'EUR',
               'ro': 'RON',
               'ru': 'EUR',
               'sk': 'EUR',
               'si': 'EUR',
               'se': 'SEK',
               'tr': 'EUR'}
# Countries supported by Newark
NEWARK_SUP = {'us': ('www.newark.com', 'USD'),
              'ca': ('canada.newark.com', 'CAD'),
              'mx': ('mexico.newark.com', 'USD')}
# Countries supported by Element14, they accept Newark and Farnell SKUs
ELEMENT14_SUP = {'cn': 'CNY',
                 'au': 'AUD',
                 'nz': 'NZD',
                 'hk': 'HKD',
                 'sg': 'SGD',
                 'my': 'MYR',
                 'ph': 'PHP',
                 'th': 'THB',
                 'in': 'INR',
                 'kr': 'KRW',
                 'vn': 'USD',
                 # The European Central Bank doesn't provide exchange for Taiwan
                 # 'tw': 'TWD'
                 }
# Countries supported by CPC
CPC_SUP = {'uk': ('cpc.farnell.com', 'GBP'),
           'ie': ('cpcireland.farnell.com', 'EUR')}
# Specs known by KiCost
SPEC_NAMES = {'power rating': 'power',
              'voltage rating': 'voltage',
              'vendorName': 'manf',
              'temperature coefficient': 'temp_coeff'}

# DIST_NAMES = ['cpc', 'farnell', 'newark']
DIST_NAMES = ['farnell', 'newark']
ENV_OPS = {'ELEMENT14_PART_API_KEY': 'key',
           'ELEMENT14_CACHE_TTL': 'cache_ttl'}
PRE_TERM = {'sku': 'id', 'key': 'any', 'mpn': 'manuPartNum'}
REPLY = {'sku': 'premierFarnellPartNumberReturn', 'key': 'keywordSearchReturn', 'mpn': 'manufacturerPartNumberSearchReturn'}

BASE_URL = 'https://api.element14.com/catalog/products'

__all__ = ['api_element14']


class Element14Error(Exception):
    pass


class Element14(object):
    def __init__(self, dist, country, key, cache):
        if dist == 'farnell':
            # Farnell Europe
            cur = FARNELL_SUP.get(country, None)
            if cur is not None:
                self.currency = cur
                self.store_info_id = country + '.farnell.com'
            else:
                # Element14 Asia and Oceania
                cur = ELEMENT14_SUP.get(country, None)
                if cur is not None:
                    self.currency = cur
                    self.store_info_id = country + '.element14.com'
                else:
                    raise Element14Error('Unsupported country `{}` for `{}`'.format(country, dist))
        elif dist == 'newark':
            # Newark North America
            url, cur = NEWARK_SUP.get(country, (None, None))
            if cur is not None:
                self.currency = cur
                self.store_info_id = url
            else:
                # Element14 Asia and Oceania
                cur = ELEMENT14_SUP.get(country, None)
                if cur is not None:
                    self.currency = cur
                    self.store_info_id = country + '.element14.com'
                else:
                    raise Element14Error('Unsupported country `{}` for `{}`'.format(country, dist))
        elif dist == 'cpc':
            # Great Britain CPC
            url, cur = CPC_SUP.get(country, (None, None))
            if cur is not None:
                self.currency = cur
                self.store_info_id = url
            else:
                raise Element14Error('Unsupported country `{}` for `{}`'.format(country, dist))
        self.key = key
        self.cache = cache

    def _extract_data(self, data, kind, term):
        res = REPLY[kind]
        if res not in data:
            raise Element14Error("Malformed reply " + str(data))
        data = data[res]
        c = None
        try:
            c = data['numberOfResults']
        except KeyError:
            pass
        if c is None:
            raise Element14Error("Missing `numberOfResults` " + str(data))
        if c == 0:
            return None
        if 'products' not in data:
            raise Element14Error("Missing `products` " + str(data))
        prod = data['products']
        if c != 1:
            warning(W_AMBIPN, "Got {} hits for {} {}".format(c, kind, term))
        return prod

    def search(self, kind, term, part={}):
        # Try to get the data from the cache
        full_name = term+'_'+self.store_info_id
        data, loaded = self.cache.load_results(kind, full_name)
        if loaded:
            debug_obsessive('Data from cache: '+pprint.pformat(data))
            return self._extract_data(data, kind, term)
        # Do a query
        params = {'callInfo.responseDataFormat': 'JSON',
                  'term': PRE_TERM[kind]+':'+term,
                  'storeInfo.id': self.store_info_id,
                  'callInfo.apiKey': self.key,
                  'resultsSettings.responseGroup': 'large'}
        if kind == 'key':
            params['resultsSettings.offset'] = '0'
            params['resultsSettings.numberOfResults'] = '10'
        params.update(part)
        debug_obsessive('Query params: '+pprint.pformat(params))
        r = requests.get(BASE_URL, params=params)
        if r.status_code != 200:
            # debug_obsessive(pprint.pformat(r.__dict__))
            raise Element14Error("Server error `{}` ({})".format(r.reason, r.status_code))
        data = r.json()
        debug_obsessive('Data from server: '+pprint.pformat(data))
        self.cache.save_results(kind, full_name, data)
        return self._extract_data(data, kind, term)

    def by_sku(self, sku):
        debug_detailed('Search by SKU '+sku)
        return self.search('sku', sku)

    def by_keyword(self, key):
        debug_detailed('Search by keyword '+key)
        return self.search('key', key)

    def by_manf_pn(self, pn):
        debug_detailed('Search by part number '+pn)
        return self.search('mpn', pn)


class api_element14(distributor_class):
    name = 'Element14'
    type = 'api'
    # Currently enabled only by request
    enabled = True
    url = 'https://partner.element14.com/'  # Web site API information.
    api_distributors = DIST_NAMES
    # Options supported by this API
    config_options = {'key': str,
                      'try_by_keyword': bool,
                      'farnell_country': ('BG', 'CZ', 'DK', 'AT', 'CH', 'DE', 'IE', 'IL', 'UK', 'ES', 'EE', 'FI', 'FR', 'HU', 'IT', 'LT',
                                          'LV', 'BE', 'NL', 'NO', 'PL', 'PT', 'RO', 'RU', 'SK', 'SI', 'SE', 'TR', 'CN', 'AU', 'NZ', 'HK',
                                          'SG', 'MY', 'PH', 'TH', 'IN', 'KR', 'VN'),
                      'newark_country': ('CA', 'US', 'MX', 'CN', 'AU', 'NZ', 'HK', 'SG', 'MY', 'PH', 'TH', 'IN', 'KR', 'VN'),
                      'cpc_country': ('IE', 'UK')}
    key = None
    countries = {'cpc': 'uk', 'farnell': 'uk', 'newark': 'us'}
    try_by_keyword = False

    @staticmethod
    def configure(ops):
        cache_ttl = 7
        cache_path = None
        for k, v in ops.items():
            if k == 'key':
                api_element14.key = v
            elif k == 'enable':
                api_element14.enabled = v
            elif k == 'try_by_keyword':
                api_element14.try_by_keyword = v
            elif k == 'cache_ttl':
                cache_ttl = v
            elif k == 'cache_path':
                cache_path = v
            elif k.endswith('_country'):
                api_element14.countries[v[:-8]] = v.lower()
        if api_element14.enabled and api_element14.key is None:
            warning(W_APIFAIL, "Can't enable Elemen14 without a `key`")
            api_element14.enabled = False
        debug_obsessive('Element14 API configured to enabled {} key {} path {}'.format(api_element14.enabled, api_element14.key, cache_path))
        if not api_element14.enabled:
            return
        # Configure the cache
        api_element14.cache = QueryCache(cache_path, cache_ttl)

    @staticmethod
    def _query_part_info(dist, country, parts, distributors, currency):
        '''Fill-in the parts with price/qty/etc info from KitSpace.'''
        debug_overview('# Getting part data from Element14 ({} {})...'.format(dist, country))
        field_cat = dist + '#'
        o = Element14(dist, country, api_element14.key, api_element14.cache)

        # Setup progress bar to track progress of server queries.
        progress = distributor_class.progress(len(parts), distributor_class.logger)
        for part in parts:
            data = None
            # Get the Element14 P/N for this part
            part_stock = part.fields.get(field_cat)
            part_manf = part.fields.get('manf', '')
            part_code = part.fields.get('manf#')
            if part_stock:
                debug_detailed('\n**** {} P/N: {}'.format(dist, part_stock))
                data = o.by_sku(part_stock)
                if data is None:
                    warning(W_NOINFO, 'The \'{}\' {} code is not valid'.format(part_stock, dist))
                    if api_element14.try_by_keyword:
                        data = o.by_keyword(part_stock)
            else:
                # No Element14 P/N, search using the manufacturer code
                if part_code:
                    if part_manf:
                        debug_detailed('\n**** Manufacturer: {} P/N: {}'.format(part_manf, part_code))
                    else:
                        debug_detailed('\n**** P/N: {}'.format(part_code))
                    data = o.by_manf_pn(part_code)
                    if data is None and api_element14.try_by_keyword:
                        data = o.by_keyword(part_code)
            if data is None:
                warning(W_NOINFO, 'No information found at {} for part/s \'{}\''.format(dist, part.refs))
            else:
                data = _select_best(data, part_manf, part.qty_total_spreadsheet)
                debug_obsessive('* Part info before adding data:')
                debug_obsessive(pprint.pformat(part.__dict__))
                debug_obsessive('* Data found:')
                debug_obsessive(pprint.pformat(data))
                ds = data.get('datasheets', None)
                if part.datasheet is None and ds is not None:
                    part.datasheet = ds[0]['url']
                if part.lifecycle is None:
                    part.lifecycle = 'obsolete' if data['productStatus'] == 'NO_LONGER_MANUFACTURED' else 'active'
                tolerance = footprint = frequency = None
                specs = {'rohs': ('RoHS', data['rohsStatusCode'])}
                for sp in data.get('attributes', []):
                    name = sp['attributeLabel']
                    name_l = name.lower()
                    value = sp['attributeValue']
                    unit = sp.get('attributeUnit', None)
                    if unit:
                        value = value + ' ' + unit
                    specs[name_l] = (name, value)
                    if name_l.endswith('tolerance'):
                        tolerance = value
                    if name_l.endswith('case style'):
                        footprint = value
                    if name_l.endswith('frequency'):
                        frequency = value
                part.update_specs(specs)
                dd = part.dd.get(dist, DistData())
                dd.qty_increment = dd.moq = data['translatedMinimumOrderQuality']
                dd.url = 'https://'+o.store_info_id+'/w/search?st='+data['sku']
                dd.part_num = data['sku']
                dd.qty_avail = data['inv']
                dd.currency = o.currency
                prices = data.get('prices', None)
                if prices:
                    dd.price_tiers = {p['from']: p['cost'] for p in prices}
                # Extra information
                dd.extra_info['desc'] = data['displayName']
                value = ''
                for spec in ('capacitance', 'resistance', 'inductance'):
                    val = specs.get(spec, None)
                    if val:
                        value += val[1] + ' '
                if value:
                    dd.extra_info['value'] = value
                if tolerance:
                    dd.extra_info['tolerance'] = tolerance
                if footprint:
                    dd.extra_info['footprint'] = footprint
                if frequency:
                    dd.extra_info['frequency'] = frequency
                for spec, name in SPEC_NAMES.items():
                    val = specs.get(spec, None)
                    if val:
                        dd.extra_info[name] = val[1]
                part.dd[dist] = dd
                debug_obsessive('* Part info after adding data:')
                debug_obsessive(pprint.pformat(part.__dict__))
                # debug_obsessive(pprint.pformat(dd.__dict__))
            progress.update(1)
        progress.close()

    @staticmethod
    def query_part_info(parts, distributors, currency):
        if len(set(DIST_NAMES).intersection(distributors)) == 0:
            # None of our distributors is used
            debug_overview('# Skipping Element14 plug-in')
            return set()
        msg = None
        try:
            for dist in DIST_NAMES:
                country = api_element14.countries[dist]
                api_element14._query_part_info(dist, country, parts, distributors, currency)
        except Element14Error as e:
            msg = e.args[0]
        if msg is not None:
            raise KiCostError(msg, ERR_SCRAPE)
        return set(DIST_NAMES)

    @staticmethod
    def from_environment(options, overwrite):
        ''' Configuration from the environment. '''
        # Configure the module from the environment
        # The command line will overwrite it using set_options()
        for k, v in ENV_OPS.items():
            api_element14._set_from_env(v, os.getenv(k), options, overwrite, api_element14.config_options)


# Ok, this is special case ... we should add others
MANF_CHANGES = {'fairchild': 'onsemi'}


def _get_price(d):
    """ Return the first price or -1 if none """
    prices = d.get('prices', None)
    return prices[0]['cost'] if prices else -1


def _get_key(d, qty):
    """ Sorting criteria for the suggested option """
    price = _get_price(d)
    stock = d['inv']
    moq = d['translatedMinimumOrderQuality']
    return (price == -1,    # Put first the ones with price
            stock == 0,     # Put first the ones in stock
            stock < qty,    # Put first the ones with enough stock
            # TODO: some tollerance to the MOQ? Like buy 20% extra
            moq > qty,      # Put first the ones with a MOQ under the quantity we need
            d['productStatus'].startswith('NO_LONGER_'),   # Put first the active components
            price,
            moq)  # At equal price suggest the lower MOQ


def _filter_by_manf(data, manf):
    """ Select the best matches according to the manufacturer """
    if not manf:
        return data
    manfs = {d['brandName'].lower() for d in data}
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
    return list(filter(lambda x: x['brandName'].lower() == best_match, data))


def _list_comp_options(data, show, msg):
    """ Debug function used to show the list of options """
    if not show:
        return
    debug_full('  - '+msg)
    for c, d in enumerate(data):
        debug_full('  {}) {} {} inv: {} moq: {} status: {} price: {}'.
                   format(c+1, d['brandName'], d['translatedManufacturerPartNumber'], d['inv'],
                          d['translatedMinimumOrderQuality'], d['productStatus'], _get_price(d)))


def _select_best(data, manf, qty):
    """ Selects the best result """
    c = len(data)
    if c == 1:
        return data[0]
    debug_obsessive(' - Choosing the best match ({} options, qty: {} manf: {})'.format(c, qty, manf))
    ultra_debug = is_debug_full()
    _list_comp_options(data, ultra_debug, 'Original list')
    # Try to choose the best manufacturer
    data2 = _filter_by_manf(data, manf)
    if data != data2:
        debug_obsessive(' - Selected manf `{}`'.format(data2[0]['brandName']))
        _list_comp_options(data2, ultra_debug, 'Manufacturer selected')
        if len(data2) == 1:
            return data2[0]
    # Sort the results according to the best availability/price
    data3 = sorted(data2, key=lambda x: _get_key(x, qty))
    _list_comp_options(data3, ultra_debug, 'Sorted')
    return data3[0]


distributor_class.register(api_element14, 100)
