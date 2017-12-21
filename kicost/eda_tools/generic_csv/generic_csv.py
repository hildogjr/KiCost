# MIT license
#
# Copyright (C) 2017 by XESS Corporation / Hildo G Jr
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
import csv # CSV file reader.
import re # Regular expression parser.
import logging

from ...kicost import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE # Debug configurations.
from ...kicost import distributors, SEPRTR
from ..eda_tools import field_name_translations, subpart_split, group_parts, split_refs

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# Add to deal with the generic CSV header purchase list.
field_name_translations.update(
    {
        'stock code': 'manf#',
        'mfr. no': 'manf#',
        'quantity': 'qty',
        'order qty': 'qty',
        'references': 'refs',
        'reference': 'refs',
        'ref': 'refs',
        'customer no': 'refs',
        'value': 'value',
        '': ''  # This is here because the header row may contain an empty field.
    }
)

GENERIC_PREFIX = 'GEN'  # Part reference prefix to use when no references are present.


def get_part_groups(in_file, ignore_fields, variant):
    '''Get groups of identical parts from an generic CSV file and return them as a dictionary.'''
    # No `variant` or `ignore_fields` are used in this function, the input is just kept by compatibily.

    logger.log(DEBUG_OVERVIEW, 'Get schematic CSV...')
    content = in_file.read()
    in_file.close()

    # Collapse multiple, consecutive tabs.
    content = re.sub('\t+', '\t', content)

    # Determine the column delimiter used in the CSV file.
    try:
        dialect = csv.Sniffer().sniff(content, [',',';','\t'])
    except csv.Error:
        # If the CSV file only has a single column of data, there may be no
        # delimiter so just set the delimiter to a comma.
        dialect = csv.Sniffer().sniff(',,,', [','])

    # The first line in the file must be the column header.
    content = content.splitlines()
    header = next(csv.reader(content,delimiter=dialect.delimiter))

    # Standardize the header titles.
    header = [field_name_translations.get(hdr.lower(),hdr.lower()) for hdr in header]

    # Examine the first line to see if it really is a header.
    # If the first line contains a column header that is not in the list of
    # allowable field names, then assume the first line is data and not a header.
    field_names = list(field_name_translations.keys()) + list(field_name_translations.values())
    if not 'manf#' in header:
        if any(col_hdr.lower() in field_names for col_hdr in header):
            content.pop(0) # It was a header by the user not identify the 'manf#' column.

        # If a column header is not in the list of field names, then there is
        # no header in the file. Therefore, create a header based on number of columns.

        # header may have a '' at the end, so remove it.
        if '' in header:
            header.remove('')

        num_cols = len(header)
        if num_cols == 1:
            header = ['manf#']
        elif num_cols == 2:
            header = ['manf#', 'refs']
        else:
            header = ['qty', 'manf#', 'refs']
    else:
        # OK, the first line is a header, so remove it from the data.
        content.pop(0) # Remove the header from the content.

    def extract_fields(row):
        fields = {}
        fields['libpart'] = 'NA'
        fields['footprint'] = 'NA'
        fields['value'] = 'NA'

        vals = next(csv.DictReader([row.replace("'", '"')], fieldnames=header, delimiter=dialect.delimiter))

        if 'refs' in vals:
            ref_str = vals['refs']
            qty = len(vals['refs'])
        elif 'qty' in vals:
            qty = int(vals['qty'])
            if qty>1:
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

        try:
            # For Python 2, create unicode versions of strings.
            fields['libpart'] = vals.get('libpart', 'Lib:???').decode('utf-8')
            fields['footprint'] = vals.get('footprint', 'Foot:???').decode('utf-8')
            fields['value'] = vals.get('value', '???').decode('utf-8')
            fields['manf#'] = vals.get('manf#', '').decode('utf-8')
        except AttributeError:
            # This is for Python 3 where the values are already unicode.
            fields['libpart'] = vals.get('libpart', 'Lib:???')
            fields['footprint'] = vals.get('footprint', 'Foot:???')
            fields['value'] = vals.get('value', '???')
            fields['manf#'] = vals.get('manf#', '')
        return refs, fields
    extract_fields.gen_cntr = 0

    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    logger.log(DEBUG_OVERVIEW, 'Get parts from hand made list...')

    # Read the each line content.
    accepted_components = {}
    for row in content:
        # Get the values for the fields in each library part (if any).
        refs, fields = extract_fields(row)
        for ref in refs:
           accepted_components[ref] = fields

    # Create some default project information.
    prj_info = {'title':'No title', 'company':'Not avaliable', 'date':'Not avaliable'}

    # Place identical parts in groups and return them.
    return group_parts(accepted_components), prj_info
