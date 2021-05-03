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
import os


__all__ = ['eda_class']


class eda_class(object):
    registered = {}

    @staticmethod
    def register(eda):
        ''' Register a new EDA class '''
        eda_class.registered[eda.name] = eda

    @staticmethod
    def get_part_groups(eda, in_file, ignore_fields, variant, distributors):
        '''Get groups of identical parts from a file and return them as a dictionary.
           @param in_file `str()` with the file name.
           @param ignore_fields `list()` fields do be ignored on the read action.
           @param variant `str()` in regular expression to match with the design version of the BOM.
           A tuple of two values is returned:
           @return `dict()` of the parts designed. The keys are the componentes references.
           @return `dict()` of project information.
        '''
        return eda_class.registered[eda].get_part_groups(in_file, ignore_fields, variant, distributors)

    @staticmethod
    def file_eda_match(file_name):
        '''@brief Verify with which EDA the file matches.

           Return the EDA name with the file matches or `None` if not founded.
           @param file_name File `str` name.
           @return Name of the module corresponding to read the file or `None`to not recognized.
        '''
        try:
            file_handle = open(file_name, 'r')
            content = file_handle.read()
        except UnicodeDecodeError:  # Python 3 assumes UTF-8, try with Latin1 if it failed
            file_handle.close()
            file_handle = open(file_name, 'r', encoding='ISO-8859-1')
            content = file_handle.read()
        file_handle.close()
        extension = os.path.splitext(file_name)[1]
        for name, cls in eda_class.registered.items():
            if cls.file_eda_match(content, extension):
                return name
        return None
