# -*- coding: utf-8 -*-

# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo G Jr
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

from .eda import eda_class
# Import and register here the file read modules.
from .eda_kicad import eda_kicad  # noqa: F401
from .eda_altium import eda_altium  # noqa: F401
from .generic_csv import generic_csv  # noqa: F401

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'


def get_registered_eda_names():
    ''' Get the names of the registered EDAs '''
    return eda_class.registered.keys()


def get_registered_eda_labels():
    ''' Get the labels of the registered EDAs '''
    return [eda.label for eda in eda_class.registered.values()]


def get_part_groups(eda, in_file, ignore_fields, variant, distributors):
    ''' Get the parts for a file using the indicated EDA '''
    return eda_class.get_part_groups(eda, in_file, ignore_fields, variant, distributors)


def file_eda_match(file_name):
    ''' Check which EDA is suitable for this file '''
    return eda_class.file_eda_match(file_name)


def get_eda_label(name):
    ''' Returns a beautiful name for the EDA '''
    return eda_class.registered[name].label


def set_edas_logger(logger):
    ''' Sets the logger used by the class '''
    eda_class.logger = logger
