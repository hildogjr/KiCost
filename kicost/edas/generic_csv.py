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

# Author information.
__author__ = 'Hildo Guillardi Júnior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'
# This module is intended to work with "generic hand made CSV" and the software:
# Proteus ISIS-ARES and AutoDesk EAGLE.

# Libraries.
import sys
import os
import time
from datetime import datetime
import csv  # CSV file reader.
import re  # Regular expression parser.
from ..global_vars import logger, DEBUG_OVERVIEW  # Debug configurations.
from .global_vars import eda_dict
from .tools import field_name_translations, remove_dnp_parts, split_refs
from ..distributors.global_vars import distributor_dict
from .eda import eda_class


# Add to deal with the generic CSV header purchase list.
field_name_translations.update(
    {
        'stock code': 'manf#',
        'mfr. no': 'manf#',
        'manpartno': 'manf#',
        'quantity': 'qty',
        'order qty': 'qty',
        'references': 'refs',
        'reference': 'refs',
        'ref': 'refs',
        'customer no': 'refs',
        'parts': 'refs',
        'part': 'refs',
        'value': 'value',
        'package': 'footprint',
        'pcb package': 'footprint',  # Used at Proteus.
        '': '',  # This is here because the header row may contain an empty field.
        # Use on `http://upverter.com/`.
        'manufacturer part number': 'manf#',
        'pcb footprint': 'footprint',
        'reference designator': 'refs',
        'part reference': 'refs',
    }
)

GENERIC_PREFIX = 'GEN'  # Part reference prefix to use when no references are present.

__all__ = ['get_part_groups']


# Place information about this EDA into the eda_tool dictionary.
eda_dict.update(
    {
        'csv': {
            'module': 'csv',  # The directory name containing this file.
            'label': 'CSV file',  # Label used on the GUI.
            'desc': 'CSV module reader for hand made BoM. Compatible with the software: Proteus and Eagle.',
            # Formatting file match.
            'file': {
                'extension': '.csv',  # File extension.
                'content': '.'  # Regular expression content match.
                }
        }
    }
)


def get_part_groups(in_file, ignore_fields, variant):
    '''Get groups of identical parts from an generic CSV file and return them as a dictionary.
       @param in_file `str()` with the file name.
       @param ignore_fields `list()` fields do be ignored on the read action.
       @param variant `str()` in regular expression to match with the design version of the BOM.
       For now, `variant`is not used on CSV read, just kept to compatibility with the other EDA submodules.
       @return `dict()` of the parts designed. The keys are the components references.
    '''

    ign_fields = [str(f.lower()) for f in ignore_fields]

    logger.log(DEBUG_OVERVIEW, '# Getting from CSV \'{}\' BoM...'.format(
                                    os.path.basename(in_file)))
    try:
        file_h = open(in_file, 'r')
        content = file_h.read()
    except UnicodeDecodeError:  # It happens with some Windows CSV files on Python 3.
        file_h.close()
        file_h = open(in_file, 'r', encoding='ISO-8859-1')
        content = file_h.read()
    file_h.close()

    # Collapse multiple, consecutive tabs.
    content = re.sub('\t+', '\t', content)

    # Determine the column delimiter used in the CSV file.
    try:
        dialect = csv.Sniffer().sniff(content, [',', ';', '\t'])
    except csv.Error:
        # If the CSV file only has a single column of data, there may be no
        # delimiter so just set the delimiter to a comma.
        dialect = csv.Sniffer().sniff(',,,', [','])

    # The first line in the file must be the column header.
    content = content.splitlines()
    logger.log(DEBUG_OVERVIEW, 'Getting CSV header...')
    header_file = next(csv.reader(content, delimiter=dialect.delimiter))
    if len(set(header_file)) < len(header_file):
        logger.warning('There is a duplicated header title in the file. This could cause loss of information.')

    # Standardize the header titles and remove the spaces before
    # and after, striping the text improve the user experience.
    header = [field_name_translations.get(hdr.strip().lower(), hdr.strip().lower()) for hdr in header_file]

    # Examine the first line to see if it really is a header.
    # If the first line contains a column header that is not in the list of
    # allowable field names, then assume the first line is data and not a header.
    field_names = list(field_name_translations.keys()) + list(field_name_translations.values())
    FIELDS_MANFCAT = ([d + '#' for d in distributor_dict] + ['manf#'])
    if not any([code in header for code in FIELDS_MANFCAT]):
        if any(col_hdr.lower() in field_names for col_hdr in header):
            content.pop(0)  # It was a header by the user not identify the 'manf#' / 'cat#' column.

        # If a column header is not in the list of field names, then there is
        # no header in the file. Therefore, create a header based on number of columns.

        # Header may have a '' at the end, so remove it.
        if '' in header:
            header.remove('')

        # Define the default header by how may columns are present at the CSV file.
        num_cols = len(header)
        if num_cols == 1:
            header = ['manf#']
        elif num_cols == 2:
            header = ['manf#', 'refs']
        else:
            header = ['qty', 'manf#', 'refs']
    else:
        # OK, the first line is a header, so remove it from the data.
        content.pop(0)  # Remove the header from the content.

    def correspondent_header_value(key, vals):
        # Get the correspondent first valid value of `vals` look from a key
        # in `header`, but using `header_file` to access `vals`. Used to get
        # the designator reference `refs` and quantity `qty`.
        idx = [i for i, x in enumerate(header) if x == key]
        value = None
        for i in idx:
            if len(idx) > 1 and value is not None and value != vals[header_file[i]]:
                logger.warning('Found different duplicated information for \'{}\': \'{}\'=!\'{}\'. Will be used the last.'.format(
                    key, value, vals[header_file[i]])
                    )
            value = vals[header_file[i]]
            if value:
                break
        return value

    def extract_fields(row):
        fields = {}

        try:
            vals = next(csv.DictReader([row.replace("'", '"')], fieldnames=header_file, delimiter=dialect.delimiter))
        except Exception:
            # If had a error when tried to read a line maybe a 'EmptyLine',
            # normally at the end of the file or after the header and before
            # the first part.
            raise Exception('EmptyLine')

        if 'refs' in header:
            ref_str = correspondent_header_value('refs', vals).strip()
            qty = len(ref_str)
        elif 'qty' in header:
            qty = int(correspondent_header_value('qty', vals))
            if qty > 1:
                ref_str = GENERIC_PREFIX + '{0}-{1}'.format(extract_fields.gen_cntr, extract_fields.gen_cntr+qty-1)
            else:
                ref_str = GENERIC_PREFIX + '{0}'.format(extract_fields.gen_cntr)
            extract_fields.gen_cntr += qty
            fields['qty'] = qty
        else:
            qty = 1
            ref_str = GENERIC_PREFIX + '{0}'.format(extract_fields.gen_cntr)
            extract_fields.gen_cntr += qty
            fields['qty'] = qty
        refs = split_refs(ref_str)

        # Extract each value.
        for (h_file, h) in zip(header_file, header):
            if h not in (ign_fields + ['refs', 'qty']):
                if sys.version_info >= (3, 0):
                    # This is for Python 3 where the values are already unicode.
                    value = vals.get(h_file)
                else:
                    # For Python 2, create unicode versions of strings.
                    value = vals.get(h_file, '').decode('utf-8')
                if value:
                    try:
                        if fields[h] != value:
                            logger.warning('Found different duplicated information for {} in the titles [\'{}\', \'{}\']: \'{}\'=!\'{}\'. Will be used \'{}\'.'
                                           .format(refs, h, h_file, fields[h], value, value)
                                           )
                    except KeyError:
                        pass
                    finally:
                        # Use the translated header title, this is used to deal
                        # with duplicated information that could be found by
                        # translating header titles that are the same for KiCost.
                        fields[h] = value
        # Set some key with default values, needed for KiCost.
        # Have to be created after the loop above because of the
        # warning in the case of trying to re-write a key.
        if 'libpart' not in fields:
            fields['libpart'] = 'Lib:???'
        if 'footprint' not in fields:
            fields['footprint'] = 'Foot:???'
        if 'value' not in fields:
            fields['value'] = '???'

        return refs, fields
    extract_fields.gen_cntr = 0

    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    logger.log(DEBUG_OVERVIEW, 'Getting parts...')

    # Read the each line content.
    accepted_components = {}
    for row in content:
        # Get the values for the fields in each library part (if any).
        try:
            refs, fields = extract_fields(row)
        except Exception:
            # If error in one line, try get the part proprieties in last one.
            continue
        for ref in refs:
            accepted_components[ref] = fields

    # Not founded project information at the file content.
    prj_info = {'title': os.path.basename(in_file),
                'company': None,
                'date': datetime.strptime(time.ctime(os.path.getmtime(in_file)), '%a %b %d %H:%M:%S %Y').strftime("%Y-%m-%d %H:%M:%S") + ' (file)'}

    return remove_dnp_parts(accepted_components, variant), prj_info


class generic_csv(eda_class):
    def __init__(self):
        pass

    @staticmethod
    def get_part_groups(in_file, ignore_fields, variant):
        return get_part_groups(in_file, ignore_fields, variant)
