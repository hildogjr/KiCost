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
import re
from collections import OrderedDict
from ..global_vars import logger, DEBUG_OVERVIEW

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
        parts, prj_info = eda_class.registered[eda].get_part_groups(in_file, ignore_fields, variant, distributors)
        return eda_class.remove_dnp_parts(parts, variant), prj_info

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

    @staticmethod
    def remove_dnp_parts(components, variant):
        '''@brief Remove the DNP parts or not assigned to the current variant.

           Remove components that are assigned to a variant that is not the current variant,
           or which are "do not populate" (DNP). (Any component that does not have a variant
           is assigned the current variant so it will not be removed unless it is also DNP.)

           @param components Part components in a `list()` of `dict()`, format given by the EDA modules.
           @return `list()` of `dict()`.
        '''
        logger.log(DEBUG_OVERVIEW, '# Removing do not populate parts...')
        accepted_components = OrderedDict()
        for ref, fields in components.items():
            # Remove DNPs.
            dnp = fields.get('local:dnp', fields.get('dnp', 0))
            try:
                dnp = float(dnp)
            except ValueError:
                pass  # The field value must have been a string.
            if dnp:
                continue
            # Get part variant. Prioritize local variants over global ones.
            variants = fields.get('local:variant', fields.get('variant', None))
            # Remove parts that are not assigned to the current variant.
            # If a part is not assigned to any variant, then it is never removed.
            if variants:
                # A part can be assigned to multiple variants. The part will not
                # be removed if any of its variants match the current variant.
                # Split the variants apart and abort the loop if any of them match.
                for v in re.split('[,;/ ]', variants):
                    if re.match(variant, v, flags=re.IGNORECASE):
                        break
                else:
                    # None of the variants matched, so skip/remove this part.
                    continue
            # The part was not removed, so add it to the list of accepted components.
            accepted_components[ref] = fields
        return accepted_components
