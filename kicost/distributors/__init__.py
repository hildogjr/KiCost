# -*- coding: utf-8 -*-

# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Júnior
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

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

from .distributor import distributor_class
# Export the ORDER_COL_USERFIELDS content
from .distributors_info import ORDER_COL_USERFIELDS  # noqa: F401

# Import and register here the API / local / scrape modules.
from .dist_local_template import dist_local_template  # noqa: F401
from .api_octopart import api_octopart  # noqa: F401
from .api_partinfo_kitspace import api_partinfo_kitspace  # noqa: F401
from .api_digikey import api_digikey  # noqa: F401
from .api_mouser import api_mouser  # noqa: F401
from .api_element14 import api_element14  # noqa: F401
from .api_tme import api_tme  # noqa: F401


#
# Some wrappers
#
def init_distributor_dict():
    distributor_class.main_init_dist_dict()


def get_dist_parts_info(parts, dist_list, currency):
    distributor_class.get_dist_parts_info(parts, dist_list, currency)


def get_registered_apis():
    return distributor_class.registered


def get_distributors_list():
    ''' List of distributors registered by the API modules '''
    return list(distributor_class.get_distributors_iter())


def get_distributors_iter():
    ''' Iterator for the distributors registered by the API modules '''
    return distributor_class.get_distributors_iter()


def get_distributor_info(name):
    ''' Gets all the information about a supported distributor.
        This information comes from the list collected from the APIs, not from the fixed template. '''
    return distributor_class.get_distributor_info(name)


def get_dist_name_from_label(label):
    ''' Returns the internal distributor name for a provided label. '''
    return distributor_class.label2name.get(label.lower())


def set_distributors_logger(logger):
    ''' Sets the logger used by the class '''
    distributor_class.logger = logger


def set_distributors_progress(cls):
    ''' Configures the class used to indicate progress '''
    distributor_class.progress = cls


def configure_apis(options):
    ''' Configure all APIs. options is a dict API -> api_options '''
    distributor_class.configure_apis(options)


def set_api_status(api, enabled):
    ''' Enable/Disable a particular API '''
    distributor_class.set_api_status(api, enabled)


def get_api_status(api):
    ''' Find if an API is enabled '''
    return distributor_class.get_api_status(api)


def is_valid_api(api):
    ''' Determines if this API is registered '''
    return distributor_class._get_api(api) is not None


def get_api_list():
    ''' Returns a list of registered APIs '''
    return [api.name for api in distributor_class.registered]


def get_api_valid_options():
    ''' Returns the vali options for each API '''
    return {api.name: api.config_options for api in distributor_class.registered}


def configure_from_environment(options, overwrite):
    distributor_class.configure_from_environment(options, overwrite)
