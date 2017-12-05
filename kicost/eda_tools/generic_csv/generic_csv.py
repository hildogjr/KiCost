# MIT license
#
# Copyright (C) 2015 by XESS Corporation / Hildo G Jr
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
# Inserted by Pasteurize tool.
#from __future__ import print_function
#from __future__ import unicode_literals
#from __future__ import division
#from __future__ import absolute_import
#import future
import csv # CSV file reader.
import re # Regular expression parser.
import logging

from ...kicost import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE
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
        'value': 'value'
    }
)

GENERIC_PREFIX = 'GEN'  # Part reference prefix to use when no references are present.


def get_part_groups(in_file, ignore_fields, variant):
    '''Get groups of identical parts from an generic CSV file and return them as a dictionary.'''
    # No `variant` of ignore field is used in this function, the input is just kept by compatibily.
    # Enven not `ignore_filds` to be ignored.
    
    logger.log(DEBUG_OVERVIEW, 'Get schematic CSV...')
    content = in_file.read()
    in_file.close()
    
    # Collapse multiple, consecutive tabs.
    content = re.sub('\t+', '\t', content)

    # Determine the column delimiter used in the CSV file.
    dialect = csv.Sniffer().sniff(content, [',',';','\t'])
    
    # The first line in the file must be the column header.
    content = content.splitlines()
    header = next(csv.reader(content,delimiter=dialect.delimiter))
    content.pop(0) # Remove the header from the content.
    # Standardize the header titles.
    header = [field_name_translations.get(title.lower(),title.lower()) for title in header]
    
    # Create some default project information.
    prj_info = {'title':'No title', 'company':'Not avaliable', 'date':'Not avaliable'}

    def extract_fields(row):
        fields = {}
        fields['libpart'] = 'NA'
        fields['footprint'] = 'NA'
        fields['value'] = 'NA'

        vals = next(csv.DictReader([row.replace("'", '"')], fieldnames=header, delimiter=dialect.delimiter))

        if 'refs' in vals:
            ref_str = vals['ref']
            qty = len(fields['refs'])
        elif 'qty' in vals:
            qty = int(vals['qty'])
            ref_str = GENERIC_PREFIX + '{0}-{1}'.format(extract_fields.gen_cntr+qty-1, extract_fields.gen_cntr)
            extract_fields.gen_cntr += qty
        else:
            qty = 1
            ref_str = GENERIC_PREFIX + '{0}'.format(extract_fields.gen_cntr)
            extract_fields.gen_cntr += qty
        refs = split_refs(ref_str)
        fields['qty'] = qty
        fields['libpart'] = vals.get('libpart', 'Lib:???')
        fields['footprint'] = vals.get('footprint', 'Foot:???')
        fields['value'] = vals.get('value', '???')
        fields['manf#'] = vals.get('manf#', '')
        return refs, fields
    extract_fields.gen_cntr = 0
    
    # Local function defined to get the corresponding fields from the CSV file.
    # def extract_fields(text):
        # '''Extract the correspondence fields in the CSV lines.'''
        # extract_fields.count_generic_ref += 1 # Counter of the generics reference.
        # fields = {}
        # values = next(csv.reader([text.replace("'",'"')],delimiter=dialect.delimiter))
        # # Default text to some fields needed for KiCost.
        # fields['libpart'] = 'Lib:Cat'
        # fields['footprint'] = 'Cat:Fooprint'
        # fields['value'] = 'Not assined' # Value of the component.
        # fields['refs'] = 'generic' # Letter used to identify groups of components.
        # refs = GENERIC_REF + '{}'.format(extract_fields.count_generic_ref)
        # fields['refs'] =  'generic'
        # for iV in range(len(values)):
            # if header[iV] == 'refs':
                # ref = values[iV]
                # if ref=='':
                    # # Enunciated the reference but empty.
                    # fields['refs'] = GENERIC_REF
                    # refs = split_refs (GENERIC_REF + 
                                       # '{1}-{2}'.format(
                                          # extract_fields.count_generic_ref,
                                          # extract_fields.count_generic_ref+values['qty']-1
                                       # )
                                      # )
                    # extract_fields.count_generic_ref += values['qty'] -1
                # refs = split_refs(ref)
                # fields['refs'] = re.findall('^\D+', refs[0])[0] # Recognize the letter(s) of the grups.
            # elif header[iV] == 'qty' and not 'refs' in header:
                # # Enunciated the quantity but not the references.
                # fields['refs'] = GENERIC_REF
                # refs = split_refs (GENERIC_REF + 
                                   # '{1}-{2}'.format(
                                      # extract_fields.count_generic_ref,
                                      # extract_fields.count_generic_ref+values['qty']-1
                                   # )
                                  # )
                # extract_fields.count_generic_ref += values['qty'] -1
            # else:
                # fields[header[iV]] = values[iV]
        # return refs, fields
    # extract_fields.count_generic_ref = 0
    
    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    logger.log(DEBUG_OVERVIEW, 'Get parts from hand made list...')
    libparts = {}
    component_groups = {}
    
    # Read the each line content.
    accepted_components = {}
    for row in content:
        # Get the values for the fields in each library part (if any).
        refs, fields = extract_fields(row)
        for ref in refs:
           accepted_components[ref] = fields

    # Place identical parts in groups and return them.
    return group_parts(accepted_components), prj_info
