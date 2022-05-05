# -*- coding: utf-8 -*-

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
from .. import DEBUG_OVERVIEW, DEBUG_OBSESSIVE, SEPRTR, W_FLDOVR
from ..distributors import get_distributors_iter

__all__ = ['eda_class', 'field_name_translations']


# Generate a dictionary to translate all the different ways people might want
# to refer to part numbers, vendor numbers, manufacture name and such.
field_name_translations = {
    # footprint
    'package': 'footprint',
    'pcb footprint': 'footprint',
    'pcb package': 'footprint',  # Used at Proteus.
    # manf#
    'mpn': 'manf#',
    'pn': 'manf#',
    'manf_num': 'manf#',
    'manf-num': 'manf#',
    'mfg_num': 'manf#',
    'mfg-num': 'manf#',
    'mfg#': 'manf#',
    'mfg part#': 'manf#',
    'mfr. no': 'manf#',
    'man#': 'manf#',
    'man_num': 'manf#',
    'man-num': 'manf#',
    'manpartno': 'manf#',
    'manufacturer part number': 'manf#',  # Use on `http://upverter.com/`.
    'mnf_num': 'manf#',
    'mnf-num': 'manf#',
    'mnf#': 'manf#',
    'mfr_num': 'manf#',
    'mfr-num': 'manf#',
    'mfr#': 'manf#',
    'part-num': 'manf#',
    'part_num': 'manf#',
    'p#': 'manf#',
    'part#': 'manf#',
    'stock code': 'manf#',
    # manf
    'manufacturer': 'manf',
    'manufacturer name': 'manf',  # Used for some web site tools to part generator in Altium.
    'mnf': 'manf',
    'man': 'manf',
    'mfg': 'manf',
    'mfr': 'manf',
    # refs
    'designator': 'refs',
    'part reference': 'refs',
    'reference': 'refs',
    'reference designator': 'refs',
    'references': 'refs',
    'customer no': 'refs',
    'parts': 'refs',
    'part': 'refs',
    # qty
    'order qty': 'qty',
    'quantity': 'qty',
    # Others fields used by KiCost and that have to be standardized.
    'pdf': 'datasheet',
    'description': 'desc',
    'nopop': 'dnp',
    'version': 'variant',
}
# Create the fields translate for each distributor submodule.
for stub in ['part#', '#', 'p#', 'pn', 'vendor#', 'vp#', 'vpn', 'num']:
    for dist in get_distributors_iter():
        if stub != '#':
            field_name_translations[dist + stub] = dist + '#'
        field_name_translations[dist + '_' + stub] = dist + '#'
        field_name_translations[dist + '-' + stub] = dist + '#'


class eda_class(object):
    registered = {}
    logger = None

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
        parts, prj_info = eda_class.registered[eda].get_part_groups(in_file, distributors)
        parts = eda_class.process_fields(parts, variant, ignore_fields, distributors)
        return eda_class.remove_dnp_parts(parts, variant), prj_info

    @staticmethod
    def process_kicost_field(f, v, new_fields, ignore_fields, distributors, name_ori, ref):
        f = f.strip()
        if SEPRTR in f:
            # DISTRIBUTOR:FIELD
            # Separate the distributor from the field name
            idx = f.index(SEPRTR)
            dist = f[:idx]
            # Is this a supported distributor?
            dist_l = dist.lower()
            if dist_l in distributors:
                # Use the lower case version
                dist = dist_l
            # Translate the field name
            f = f[idx+1:].lower()
            if f in ignore_fields:
                return
            f = field_name_translations.get(f, f)
            if f in ignore_fields:
                return
            # Join both again
            f = dist + SEPRTR + f
        else:
            # FIELD
            # No distributor in the name
            # Adapt it
            f = f.lower()
            if f in ignore_fields:
                return
            f = field_name_translations.get(f, f)
            if f in ignore_fields:
                return
            # Is distributor related?
            if f in ('cat#', 'pricing', 'link'):
                # Add it to the default local distributor
                eda_class.logger.log(DEBUG_OBSESSIVE, 'Assigning name "{}" to "Local" distributor'.format(f))
                f = 'Local:' + f
        # Note: here we allow a field to "clear" another definition (assigning an empty value)
        # This is because we assume that "kicost*" fields are defined on purpose, not just inherited from the library
        new_fields[f] = v.strip()
        eda_class.logger.log(DEBUG_OBSESSIVE, '{} Field {} -> {}={}'.format(ref, name_ori, f, v))

    @staticmethod
    def process_fields(parts, variant, ignore_fields, distributors):
        new_parts = OrderedDict()
        for ref, fields in parts.items():
            new_fields = OrderedDict()
            # Add the fields from lowest to highest priority.
            # We even add empty fields, so we can "clear" a field using a higher priority mechanism.
            # 1) All fields without SEPRTR (lowest priority)
            for f, v in fields.items():
                old_name = f
                if SEPRTR in f:
                    continue
                # Just translate it
                f = f.lower().strip()
                if f in ignore_fields:
                    continue
                f = field_name_translations.get(f, f)
                if f in ignore_fields:
                    continue
                # Trim extra spaces in the value
                v = v.strip()
                already_defined = f in new_fields
                if not v and already_defined:
                    # For regular fields we avoid one alias clearing another.
                    # Example: if manf# was defined as XXX and now we have mnp='' we avoid getting manf#=''
                    continue
                if already_defined and new_fields[f]:
                    eda_class.logger.warning(W_FLDOVR+'Warning: in {} overwriting {}={} with {}={}'.format(ref, f, new_fields[f], old_name, v))
                new_fields[f] = v
            # 2) kicost:FIELD
            for f, v in fields.items():
                if f.startswith('kicost' + SEPRTR):
                    eda_class.process_kicost_field(f[7:], v, new_fields, ignore_fields, distributors, f, ref)
            # 3) kicost.VARIANT:  (highest priority)
            for f, v in fields.items():
                if not (SEPRTR in f and f.startswith('kicost.')):
                    continue
                sep_pos = f.index(SEPRTR)
                var = f[7:sep_pos]
                if not re.match(variant, var, flags=re.IGNORECASE):
                    # Not for the current variant
                    continue
                name = f[sep_pos+1:]
                eda_class.logger.log(DEBUG_OBSESSIVE, 'Matched Variant ... ' + var + '.' + name)
                eda_class.process_kicost_field(name, v, new_fields, ignore_fields, distributors, f, ref)
            # TODO: What about the other cases?
            # * Has ':' but doesn't start with "kicost"
            new_parts[ref] = new_fields
        return new_parts

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
        eda_class.logger.log(DEBUG_OVERVIEW, '# Removing do not populate parts...')
        accepted_components = OrderedDict()
        for ref, fields in components.items():
            # Remove DNPs.
            dnp = fields.get('dnp', '0')
            # Interpret empty strings as 0. See #471 discussion.
            if dnp == '':
                dnp = '0'
            try:
                dnp = float(dnp)
            except ValueError:
                # The field value must have been a string.
                # The docs says "any string" is DNP enabled.
                dnp = 1
            if dnp:
                continue
            # Get part variant. Prioritize local variants over global ones.
            variants = fields.get('variant', None)
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
