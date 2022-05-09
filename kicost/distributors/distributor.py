# -*- coding: utf-8 -*-

# MIT license
#
# Copyright (c) 2020-2022 Salvador E. Tropea
# Copyright (c) 2020-2022 Instituto Nacional de Tecnología Industrial
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
__webpage__ = 'https://github.com/set-soft/'
__company__ = 'INTI-CMNB - Argentina'

import copy
import os
import logging
import tqdm
# QueryCache dependencies:
import pickle
import time
from .. import DEBUG_HTTP_HEADERS, DEBUG_HTTP_RESPONSES
from ..global_vars import DEFAULT_CURRENCY, BASE_OP_TYPES, W_NOAPI
from .distributors_info import distributors_info

__all__ = ['distributor_class']


class TqdmLoggingHandler(logging.Handler):
    '''Overload the class to write the logging through the `tqdm`.'''
    def __init__(self, stream, level=logging.NOTSET):
        super(self.__class__, self).__init__(level)
        self.stream = stream

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg, file=self.stream)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)


class QueryCache(object):
    ''' Components queries cache implementation '''
    def __init__(self, path, ttl):
        self.path = path
        self.ttl_min = ttl*24*60
        self.suffix = ''

    def get_name(self, prefix, name):
        return os.path.join(self.path, prefix + '_' + name.replace('/', '_') + self.suffix + ".dat")

    def save_results(self, prefix, name, results):
        ''' Saves the results to the cache '''
        with open(self.get_name(prefix, name), "wb") as fh:
            pickle.dump(results, fh, protocol=2)

    def load_results(self, prefix, name):
        ''' Loads the results from the cache, must be implemented by KiCost '''
        file = self.get_name(prefix, name)
        if not os.path.isfile(file):
            return None, False
        mtime = os.path.getmtime(file)
        ctime = time.time()
        dif_minutes = int((ctime-mtime)/60)
        if self.ttl_min < 0 or (self.ttl_min > 0 and dif_minutes <= self.ttl_min):
            with open(file, "rb") as fh:
                result = pickle.loads(fh.read())
            return result, True
        # Cache expired
        return None, False


class distributor_class(object):
    registered = []
    priorities = []
    logger = None
    # distributor_dict contains the available distributors.
    # The distributors are added by the api_*/dist_*/scrape_* modules.
    # The information of each distributor is copied from distributors_info
    # Some modules can add new distributors, not found on distributors_info (from data in the fields)
    # The list of *used* distributors is handled separately.
    distributor_dict = {}
    label2name = {}
    # Options supported by this API
    config_options = {}

    @staticmethod
    def register(api, priority):
        index = 0
        for idx, prio in enumerate(distributor_class.priorities):
            index = idx
            if prio < priority:
                break
        else:
            index += 1
        distributor_class.registered.insert(index, api)
        distributor_class.priorities.insert(index, priority)

    @staticmethod
    def update_distributors(parts, distributors):
        """ This is used by the Local distributors mechanism to discover user defined distributors """
        pass

    @staticmethod
    def get_dist_parts_info(parts, distributors, currency=DEFAULT_CURRENCY):
        ''' Get the parts info using the modules API/Scrape/Local.'''
        from .log__ import debug_overview
        debug_overview('Starting to search using distributors: {}'.format(distributors))
        # Discover user defined distributors
        for api in distributor_class.registered:
            if api.enabled:
                api.update_distributors(parts, distributors)
        debug_overview('Distributors after local discovery: {}'.format(distributors))
        # Now look for the parts
        remaining = set(distributors)
        for api in distributor_class.registered:
            debug_overview('Considering: {} {}'.format(api.name, api.api_distributors))
            if api.enabled and len(remaining.intersection(api.api_distributors)):
                if api.url:
                    url = ' ({})'.format(api.url)
                else:
                    url = ''
                distributor_class.logger.info('- {} [{}]{}'.format(api.name, api.type, url))
                solved = api.query_part_info(parts, list(remaining), currency)
                if solved:
                    remaining -= solved
                debug_overview('Distributors solved {}, remaining {}'.format(solved, remaining))

    @classmethod
    def init_dist_dict(cls):
        if cls.enabled and cls.type != 'local':   # Local distributors are collected from the components
            distributor_class.add_distributors(cls.api_distributors)

    @staticmethod
    def main_init_dist_dict():
        ''' Initialize and update the dictionary of the registered distributors classes.'''
        # Clear distributor_dict, then let all distributor modules recreate their entries.
        distributor_class.distributor_dict = {}
        distributor_class.label2name = {}
        for api in distributor_class.registered:
            api.init_dist_dict()

    @staticmethod
    def get_distributors_iter():
        return distributor_class.distributor_dict.keys()

    @staticmethod
    def add_distributors(dists):
        ''' Adds a copy of the distributor info to the supported '''
        for dist in dists:
            # Here we copy the available distributors from distributors_info
            # We use a copy so they can be restored just calling this init again
            data = distributors_info[dist]
            distributor_class.distributor_dict[dist] = copy.deepcopy(data)
            distributor_class.label2name[data.label.name.lower()] = dist

    @staticmethod
    def add_distributor(name, data):
        ''' Adds a distributor to the list of supported '''
        distributor_class.distributor_dict[name] = data
        distributor_class.label2name[data.label.name.lower()] = name

    @staticmethod
    def get_distributor_template(name):
        ''' Get a copy of the distributor info from the original structure.
            Used internaly from the API to add distributors derived from others. '''
        return copy.deepcopy(distributors_info[name])

    @staticmethod
    def get_distributor_info(name):
        ''' Gets all the information about a supported distributor.
            This information comes from the list collected from the APIs, not from the fixed template. '''
        return distributor_class.distributor_dict[name]

    @staticmethod
    def log_request(url, data):
        distributor_class.logger.log(DEBUG_HTTP_HEADERS, 'URL ' + url + ' query:')
        distributor_class.logger.log(DEBUG_HTTP_HEADERS, data)
        if os.environ.get('KICOST_LOG_HTTP'):
            with open(os.environ['KICOST_LOG_HTTP'], 'at') as f:
                f.write(data + '\n')

    @staticmethod
    def log_response(response):
        distributor_class.logger.log(DEBUG_HTTP_RESPONSES, response.text)
        distributor_class.logger.log(DEBUG_HTTP_RESPONSES, 'Status Code: <{}>'.format(response.status_code))
        if os.environ.get('KICOST_LOG_HTTP'):
            with open(os.environ['KICOST_LOG_HTTP'], 'at') as f:
                f.write(response.text + '\n')

    @staticmethod
    def _get_api(api):
        # We currently assume the API is registered
        return next((x for x in distributor_class.registered if x.name == api), None)

    @staticmethod
    def configure_apis(options):
        ''' Configure all APIs. options is a dict API -> api_options '''
        for api_name, ops in options.items():
            api = distributor_class._get_api(api_name)
            if api is not None:
                api.configure(ops)

    @staticmethod
    def set_api_status(api_name, enabled):
        ''' Enable/Disable a particular API '''
        api = distributor_class._get_api(api_name)
        if api:
            api.enabled = enabled
        else:
            distributor_class.logger.warning(W_NOAPI+'No API registered as `{}`'.format(api_name))

    @staticmethod
    def get_api_status(api):
        ''' Find if an API is enabled '''
        return distributor_class._get_api(api).enabled

    @staticmethod
    def from_environment(options, overwrite):
        ''' Default configuration from the environment. Just nothing. '''
        pass

    @staticmethod
    def _set_from_env(key, value, options, overwrite, d_types=None):
        ''' Helper function to implement `from_environment`. '''
        if value is not None and (overwrite or key not in options):
            if d_types:
                # If we know the valid data type for the value ensure it
                tp = d_types.get(key, None)
                tp = BASE_OP_TYPES.get(key, tp)
                if not isinstance(tp, type):
                    # Solve the case where more than one data type is allowed
                    tp = tp[0]
                # This is a cast
                value = tp(value)
            options[key] = value

    @staticmethod
    def configure_from_environment(options, overwrite):
        ''' Configure all APIs using environment variables.
            If overwrite is True the API should replace the current option '''
        for api in distributor_class.registered:
            api.from_environment(options[api.name], overwrite)

    # Abstract methods, implemented in distributor specific modules.
    @staticmethod
    def query():
        '''Send query to server and return results.'''
        raise NotImplementedError()

    @staticmethod
    def query_part_info():
        ''' Get the parts info of one distributor class.'''
        raise NotImplementedError()
