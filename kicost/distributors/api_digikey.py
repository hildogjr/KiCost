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

# KiCost definitions.
from .. import DistData, KiCostError, W_NOINFO, ERR_SCRAPE, W_APIFAIL
# Distributors definitions.
from .distributor import distributor_class, QueryCache
from .log__ import debug_detailed, debug_overview, debug_obsessive, warning

available = True
try:
    from kicost_digikey_api_v3 import by_digikey_pn, by_manf_pn, by_keyword, DigikeyError, DK_API
except ImportError:
    available = False

    class DK_API(object):
        api_ops = None

DIST_NAME = 'digikey'
# Specs known by KiCost
SPEC_NAMES = {'tolerance': 'tolerance',
              'power (watts)': 'power',
              'voltage - rated': 'voltage',
              'manufacturer': 'manf',
              'size / dimension': 'size',
              'temperature coefficient': 'temp_coeff',
              'frequency': 'frequency',
              'package / case': 'footprint'}
ENV_OPS = {'DIGIKEY_STORAGE_PATH': 'cache_path',
           'DIGIKEY_CLIENT_ID': 'client_id',
           'DIGIKEY_CLIENT_SECRET': 'client_secret',
           'DIGIKEY_CLIENT_SANDBOX': 'sandbox',
           'DIGIKEY_CACHE_TTL': 'cache_ttl'}

__all__ = ['api_digikey']


class api_digikey(distributor_class):
    name = 'Digi-Key'
    type = 'api'
    # Currently enabled only by request
    enabled = available
    url = 'https://developer.digikey.com/'  # Web site API information.
    api_distributors = [DIST_NAME]
    # Options supported by this API
    config_options = {'client_id': str,
                      'client_secret': str,
                      'sandbox': bool,
                      'locale_site': ('US', 'CA', 'JP', 'UK', 'DE', 'AT', 'BE', 'DK', 'FI', 'GR', 'IE',
                                      'IT', 'LU', 'NL', 'NO', 'PT', 'ES', 'KR', 'HK', 'SG', 'CN', 'TW',
                                      'AU', 'FR', 'IN', 'NZ', 'SE', 'MX', 'CH', 'IL', 'PL', 'SK', 'SI',
                                      'LV', 'LT', 'EE', 'CZ', 'HU', 'BG', 'MY', 'ZA', 'RO', 'TH', 'PH'),
                      'locale_language': ('en', 'ja', 'de', 'fr', 'ko', 'zhs,' 'zht', 'it', 'es', 'he',
                                          'nl', 'sv', 'pl', 'fi', 'da', 'no'),
                      'locale_currency': ('USD', 'CAD', 'JPY', 'GBP', 'EUR', 'HKD', 'SGD', 'TWD', 'KRW',
                                          'AUD', 'NZD', 'INR', 'DKK', 'NOK', 'SEK', 'ILS', 'CNY', 'PLN',
                                          'CHF', 'CZK', 'HUF', 'RON', 'ZAR', 'MYR', 'THB', 'PHP'),
                      'locale_ship_to_country': str}

    @staticmethod
    def configure(ops):
        DK_API.api_ops = {}
        cache_ttl = 7
        cache_path = None
        for k, v in ops.items():
            if k == 'client_id':
                DK_API.id = v
            elif k == 'client_secret':
                DK_API.secret = v
            elif k == 'enable' and available:
                api_digikey.enabled = v
            elif k == 'sandbox':
                DK_API.sandbox = v
            elif k == 'cache_ttl':
                cache_ttl = v
            elif k == 'cache_path':
                cache_path = v
            elif k.startswith('locale_'):
                DK_API.api_ops[k] = v
        if api_digikey.enabled and (DK_API.id is None or DK_API.secret is None or cache_path is None):
            warning(W_APIFAIL, "Can't enable Digi-Key without a `client_id`, `client_secret` and `cache_path`")
            api_digikey.enabled = False
        debug_obsessive('Digi-Key API configured to enabled {} id {} secret {} path {}'.
                        format(api_digikey.enabled, DK_API.id, DK_API.secret, cache_path))
        if not api_digikey.enabled:
            return
        # Try to configure the plug-in
        cache = QueryCache(cache_path, cache_ttl)
        try:
            DK_API.configure(cache, a_logger=distributor_class.logger)
        except DigikeyError as e:
            warning(W_APIFAIL, 'Failed to init Digi-Key API, reason: {}'.format(e.args[0]))
            api_digikey.enabled = False

    @staticmethod
    def _query_part_info(parts, distributors, currency):
        '''Fill-in the parts with price/qty/etc info from KitSpace.'''
        if DIST_NAME not in distributors:
            debug_overview('# Skipping Digi-Key plug-in')
            return
        debug_overview('# Getting part data from Digi-Key...')
        field_cat = DIST_NAME + '#'

        # Setup progress bar to track progress of server queries.
        progress = distributor_class.progress(len(parts), distributor_class.logger)
        for part in parts:
            data = None
            # Get the Digi-Key P/N for this part
            part_stock = part.fields.get(field_cat)
            if part_stock:
                debug_detailed('\n**** Digi-Key P/N: {}'.format(part_stock))
                o = by_digikey_pn(part_stock)
                data = o.search()
                if data is None:
                    warning(W_NOINFO, 'The \'{}\' Digi-Key code is not valid'.format(part_stock))
                    o = by_keyword(part_stock)
                    data = o.search()
            else:
                # No Digi-Key P/N, search using the manufacturer code
                part_manf = part.fields.get('manf', '')
                part_code = part.fields.get('manf#')
                if part_code:
                    if part_manf:
                        debug_detailed('\n**** Manufacturer: {} P/N: {}'.format(part_manf, part_code))
                    else:
                        debug_detailed('\n**** P/N: {}'.format(part_code))
                    o = by_manf_pn(part_code)
                    data = o.search()
                    if data is None:
                        o = by_keyword(part_code)
                        data = o.search()
            if data is None:
                warning(W_NOINFO, 'No information found at Digi-Key for part/s \'{}\''.format(part.refs))
            else:
                debug_obsessive('* Part info before adding data:')
                debug_obsessive(pprint.pformat(part.__dict__))
                debug_obsessive('* Data found:')
                debug_obsessive(str(data))
                part.datasheet = data.primary_datasheet
                part.lifecycle = data.product_status.lower()
                specs = {sp.parameter.lower(): (sp.parameter, sp.value) for sp in data.parameters}
                specs['rohs'] = ('RoHS', data.ro_hs_status)
                part.update_specs(specs)
                dd = part.dd.get(DIST_NAME, DistData())
                dd.qty_increment = dd.moq = data.minimum_order_quantity
                dd.url = data.product_url
                dd.part_num = data.digi_key_part_number
                dd.qty_avail = data.quantity_available
                dd.currency = data.search_locale_used.currency
                dd.price_tiers = {p.break_quantity: p.unit_price for p in data.standard_pricing}
                # Extra information
                if data.product_description:
                    dd.extra_info['desc'] = data.product_description
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
                debug_obsessive(pprint.pformat(dd.__dict__))
            progress.update(1)
        progress.close()

    @staticmethod
    def query_part_info(parts, distributors, currency):
        msg = None
        try:
            api_digikey._query_part_info(parts, distributors, currency)
        except DigikeyError as e:
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
            api_digikey._set_from_env(v, os.getenv(k), options, overwrite, api_digikey.config_options)


distributor_class.register(api_digikey, 100)
