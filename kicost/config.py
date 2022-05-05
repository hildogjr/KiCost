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

import sys
import os
from .global_vars import ERR_KICOSTCONFIG, W_CONFIG, BASE_OP_TYPES
from .distributors import is_valid_api, get_api_list, get_api_valid_options
from . import debug_detailed, debug_obsessive, error, warning
try:
    import yaml
    CONFIG_ENABLED = True
except ImportError:
    CONFIG_ENABLED = False

CONFIG_FILE = 'config.yaml'
cache_ttl = 7
cache_path = os.path.expanduser('~') + '/.cache/kicost'
api_options = {}
config_file_path = None


def config_error(msg):
    error("In configuration file: "+msg)
    sys.exit(ERR_KICOSTCONFIG)


def config_number(k, v):
    if not isinstance(v, (int, float)):
        config_error("`{}` must be a number ({})".format(k, v))
    return v


def config_path(k, v):
    if not isinstance(v, str):
        config_error("`{}` must be a string ({})".format(k, v))
    if v[0] == '~':
        v = os.path.expanduser(v)
    elif v[0] == '.':
        v = os.path.join(config_file_path, v)
    return os.path.abspath(v)


def config_force_ttl(ttl):
    for k, v in api_options.items():
        v['cache_ttl'] = ttl


def config_force_path(path):
    path = os.path.abspath(path)
    for k, v in api_options.items():
        v['cache_path'] = os.path.join(path, k)


def parse_kicost_section(d):
    if not isinstance(d, dict):
        config_error("`KiCost` section must be a dict ({})".format(d))
    # Check the config version
    version = config_number('version', d.get('version', 1))
    if version > 1:
        config_error("Only version 1 is supported ({})".format(version))
    # Now the rest of the options
    for k, v in d.items():
        if k == 'cache_ttl':
            global cache_ttl
            cache_ttl = config_number(k, v)
        elif k == 'cache_path':
            global cache_path
            cache_path = config_path(k, v)
        elif k == 'version':
            pass
        else:
            warning(W_CONFIG, "Unknown config option `kicost.{}`".format(k))


def _type_str(a):
    if isinstance(a, type):
        return a.__name__
    return str([v.__name__ for v in a])


def parse_apis_section(d):
    if not isinstance(d, dict):
        config_error("`APIs` section must be a dict ({})".format(d))
    valid_ops = get_api_valid_options()
    for k, v in d.items():
        if not is_valid_api(k):
            warning(W_CONFIG, 'Unknown API `{}`'.format(k))
            continue
        v_ops = dict(valid_ops[k], **BASE_OP_TYPES)
        if v is None:
            continue
        # Make sure the options are of the correct value
        for op, value in v.items():
            if op not in v_ops:
                warning(W_CONFIG, 'Unknown option `{}` for API `{}`'.format(op, k))
            else:
                v_op = v_ops[op]
                if isinstance(v_op, type) or (isinstance(v_op, tuple) and isinstance(v_op[0], type)):
                    # One or more types
                    if not isinstance(value, v_op):
                        config_error('{}.{} must be `{}`, not `{}`'.format(k, op, _type_str(v_op), type(value).__name__))
                else:
                    tp = type(v_op[0])
                    # One or more values
                    if not isinstance(value, tp):
                        config_error('{}.{} must be `{}`, not `{}`'.format(k, op, _type_str(tp), type(value).__name__))
                    if value not in v_op:
                        config_error('{}.{} must be one of `{}`'.format(k, op, v_op))

        # Make the cache_path absolute
        cp = v.get('cache_path', None)
        if cp:
            v['cache_path'] = config_path('cache_path', cp)
        global api_options
        api_options[k] = v


def load_config(file=None):
    if file is None:
        file = os.path.expanduser(os.path.join('~', '.config', 'kicost', CONFIG_FILE))
    else:
        if not os.path.isfile(file):
            error('Missing config file {}.'.format(file))
            sys.exit(2)
    file = os.path.abspath(file)
    if os.path.isfile(file):
        global config_file_path
        config_file_path = os.path.dirname(file)
        try:
            data = yaml.safe_load(open(file))
        except yaml.YAMLError as e:
            config_error("Error loading YAML "+str(e))
        for k, v in data.items():
            k_l = k.lower()
            if k_l == 'kicost':
                parse_kicost_section(v)
            elif k_l == 'apis' or k_l == 'api':
                parse_apis_section(v)
            else:
                warning(W_CONFIG, 'Unknown section `{}` in config file'.format(k))
        debug_obsessive('Loaded API options {}'.format(api_options))
    for api in get_api_list():
        if api not in api_options:
            api_options[api] = {}
        # Transfer defaults
        ops = api_options[api]
        if 'cache_ttl' not in ops:
            ops['cache_ttl'] = cache_ttl
        if 'cache_path' not in ops:
            path = os.path.join(cache_path, api)
            ops['cache_path'] = path
        path = ops['cache_path']
        if not os.path.exists(path):
            os.makedirs(path)
    debug_detailed('API options with defaults {}'.format(api_options))
    return api_options
