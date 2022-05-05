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
from datetime import datetime
from collections import OrderedDict
import csv  # CSV file reader.
import re  # Regular expression parser.
from .tools import field_name_translations, split_refs
from .eda import eda_class
from .log__ import debug_overview, warning
from .. import KiCostError, ERR_INPUTFILE, W_DUPWRONG


GENERIC_PREFIX = 'GEN'  # Part reference prefix to use when no references are present.

__all__ = ['generic_csv']


def correspondent_header_value(key, vals, header, header_file):
    # Get the correspondent first valid value of `vals` look from a key
    # in `header`, but using `header_file` to access `vals`. Used to get
    # the designator reference `refs` and quantity `qty`.
    idx = [i for i, x in enumerate(header) if x == key]
    value = None
    for i in idx:
        if len(idx) > 1 and value is not None and value != vals[header_file[i]]:
            warning(W_DUPWRONG, 'Found different duplicated information for \'{}\': \'{}\'=!\'{}\'. Will be used the last.'.format(
                key, value, vals[header_file[i]]))
        value = vals[header_file[i]]
        if value:
            break
    return value


def extract_fields(row, header, header_file, dialect, gen_cntr):
    fields = {}

    try:
        vals = next(csv.DictReader([row.replace("'", '"')], fieldnames=header_file, delimiter=dialect.delimiter))
    except Exception:
        # If had a error when tried to read a line maybe a 'EmptyLine',
        # normally at the end of the file or after the header and before
        # the first part.
        raise KiCostError('Empty line in CSV?!', ERR_INPUTFILE)

    if 'refs' in header:
        ref_str = correspondent_header_value('refs', vals, header, header_file).strip()
        qty = len(ref_str)
    elif 'qty' in header:
        qty = int(correspondent_header_value('qty', vals, header, header_file))
        if qty > 1:
            ref_str = GENERIC_PREFIX + '{0}-{1}'.format(gen_cntr, gen_cntr+qty-1)
        else:
            ref_str = GENERIC_PREFIX + '{0}'.format(gen_cntr)
        gen_cntr += qty
        fields['qty'] = str(qty)
    else:
        qty = 1
        ref_str = GENERIC_PREFIX + '{0}'.format(gen_cntr)
        gen_cntr += qty
        fields['qty'] = str(qty)
    refs = split_refs(ref_str)

    # Extract each value.
    for (h_file, h) in zip(header_file, header):
        if h not in ('refs', 'qty'):
            if sys.version_info >= (3, 0):
                # This is for Python 3 where the values are already unicode.
                value = vals.get(h_file)
            else:
                # For Python 2, create unicode versions of strings.
                value = vals.get(h_file, '').decode('utf-8')
            try:
                if value and fields[h] != value:
                    warning(W_DUPWRONG, 'Found different duplicated information for {} in '
                            'the titles [\'{}\', \'{}\']: \'{}\'=!\'{}\'. Will be used \'{}\'.'.
                            format(refs, h, h_file, fields[h], value, value))
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

    return refs, fields, gen_cntr


def get_part_groups(in_file, distributors):
    '''Get groups of identical parts from an generic CSV file and return them as a dictionary.
       @param in_file `str()` with the file name.
       @return `dict()` of the parts designed. The keys are the components references.
    '''
    debug_overview('# Getting from CSV \'{}\' BoM...'.format(
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
    debug_overview('Getting CSV header...')
    header_file = next(csv.reader(content, delimiter=dialect.delimiter))
    if len(set(header_file)) < len(header_file):
        warning(W_DUPWRONG, 'There is a duplicated header title in the file. This could cause loss of information.')

    # Standardize the header titles and remove the spaces before
    # and after, striping the text improve the user experience.
    header = [field_name_translations.get(hdr.strip().lower(), hdr.strip().lower()) for hdr in header_file]

    # Examine the first line to see if it really is a header.
    # If the first line contains a column header that is not in the list of
    # allowable field names, then assume the first line is data and not a header.
    field_names = list(field_name_translations.keys()) + list(field_name_translations.values())
    FIELDS_MANFCAT = ([d + '#' for d in distributors] + ['manf#'])
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

    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    debug_overview('Getting parts...')

    # Read the each line content.
    accepted_components = OrderedDict()
    gen_cntr = 0
    for row in content:
        # Get the values for the fields in each library part (if any).
        refs, fields, gen_cntr = extract_fields(row, header, header_file, dialect, gen_cntr)
        for ref in refs:
            accepted_components[ref] = fields

    # No project information in CSVs
    prj_info = {'title': os.path.basename(in_file),
                'company': None,
                'date': datetime.fromtimestamp(os.path.getmtime(in_file)).strftime("%Y-%m-%d %H:%M:%S") + ' (file)'}

    return accepted_components, prj_info


class generic_csv(eda_class):
    name = 'csv'
    label = 'CSV file'  # Label used on the GUI.
    desc = 'CSV module reader for hand made BoM. Compatible with the software: Proteus and Eagle.'

    @staticmethod
    def get_part_groups(in_file, distributors):
        return get_part_groups(in_file, distributors)

    @staticmethod
    def file_eda_match(content, extension):
        ''' Returns True if this EDA can handle this file. '''
        return extension == '.csv'


eda_class.register(generic_csv)
