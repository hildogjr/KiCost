# MIT license
#
# Copyright (C) 2020 by Hildo Guillardi Junior
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

# Libraries.


from .global_vars import *


__all__ = ['eda_class']


class eda_class(object):
    def __init__(self, name, logger):
        self.name = name
        self.logger = logger


def get_part_groups(in_file):
    '''Get groups of identical parts from an generic CSV file and return them as a dictionary.
       @param in_file `str()` with the file name.
       @param ignore_fields `list()` fields do be ignored on the read action.
       @param variant `str()` in regular expression to match with the design version of the BOM.
       For now, `variant`is not used on CSV read, just kept to compatibility with the other EDA submodules.
       @return `dict()` of the parts designed. The keys are the components references.
    '''

    # TODO this file aims to be a base class file for create all the BOM readers.
