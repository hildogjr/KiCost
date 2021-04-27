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
__author__ = 'Max Maisel'
__webpage__ = 'https://github.com/mmmaisel/'

import kicost.global_vars as gv

__all__ = ['distributor_class']


class distributor_class(object):
    registered = []
    priorities = []

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
    def get_dist_parts_info(parts, distributors, currency=gv.DEFAULT_CURRENCY):
        ''' Get the parts info using the modules API/Scrape/Local.'''
        for api in distributor_class.registered:
            if api.enabled:
                api.query_part_info(parts, distributors, currency)

    @staticmethod
    def init_dist_dict():
        ''' Initialize and update the dictionary of the registered distributors classes.'''
        # Clear distributor_dict, then let all distributor modules recreate their entries.
        gv.distributor_dict = {}
        for api in distributor_class.registered:
            api.init_dist_dict()

    # Abstract methods, implemented in distributor specific modules.
    @staticmethod
    def query():
        '''Send query to server and return results.'''
        raise NotImplementedError()

    @staticmethod
    def query_part_info():
        ''' Get the parts info of one distributor class.'''
        raise NotImplementedError()
