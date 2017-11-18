# MIT license
#
# Copyright (C) 2015 by XESS Corporation
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

field_name_translations = dict()
logger = logging.getLogger('kicost')
DEBUG_OVERVIEW = logging.DEBUG
DEBUG_DETAILED = logging.DEBUG-1
DEBUG_OBSESSIVE = logging.DEBUG-2
SEPRTR=':'

#from ...kicost import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE
#from ...kicost import distributors
#from ..eda_tools import field_name_translations
#from ..eda_tools import subpart_split

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
        'references': 'reference',
        'ref':'reference',
        'customer no': 'reference',
        'value': 'value'
    }
)


# Temporary class for storing part group information.
class IdenticalComponents(object):
    pass

def get_part_groups_generic_csv(in_file, ignore_fields, variant):
    '''Get groups of identical parts from an generic CSV file and return them as a dictionary.'''
    # No variant of ignore field is used in this function, the input is just kept by compatibily.
    
    logger.log(DEBUG_OVERVIEW, 'Get schematic CSV...')
    content = in_file.read()
    in_file.close()
    
    # Try to get the dialect, sometimes differents OS and languages of
    # than put differents delimiters to the values in a CSV file.
    dialect = csv.Sniffer().sniff(content, [',',';','\t'])
    
    # Check if have header, if don't assumes a standart column sequence: qty, manf#, refs.
    is_headed = csv.Sniffer().has_header(content)
    content = content.splitlines()
    if not is_headed:
        if len(split_col_func.findall(content[0]))==1:
            header = ['manf#']
        elif len(split_col_func.findall(content[0]))==2:
            header = ['manf#', 'refs']
        else:
            header = ['qty', 'manf#', 'refs']
    else:
        header = next(csv.reader(content,delimiter=dialect.delimiter))
        content = content[1:] # Remove the header from the content.
        # Use the dictionary to standarize ti header titles.
        for idx in range(len(header)):
            title = header[idx].lower()
            header[idx] = field_name_translations.get(title,title)
    
    # Loval function defined to get the conrrespondence fileds from the CSV file.
    def extract_fields(text):
        '''Extract the correspondence fields in the CSV lines.'''
        values = next(csv.reader([text.replace("'",'"')],delimiter=dialect.delimiter))
        fields = {}
        # Default text to some fields needed for KiCost.
        fields['footprint']='Fooprint'
        fields['libpart']='Lib'
        fields['value']='Not assined'
        fields['reference']='generic'
        for iV in range(len(values)):
            fields[header[iV]] = values[iV]
        return fields
    
    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    logger.log(DEBUG_OVERVIEW, 'Get parts from hand made list...')
    libparts = {}
    component_groups = {}
    
    # Read the each line content.
    for row in content:
        # Get the values for the fields in each library part (if any).
        fields = extract_fields(row)
        
        print('   >>>>   ', fields)
        
        # Store the field dict under the key made from the
        # concatenation of the library and part names.
        #~ libparts[str(fields['libpart'] + SEPRTR + fields['reference'])] = fields
        libparts[fields['libpart'] + SEPRTR + fields['reference']] = fields
        
        # Also have to store the fields under any part aliases.
#        try:
#            for alias in p.find('aliases').find_all('alias'):
#                libparts[str(fields['libpart'] + SEPRTR + alias.string)] = fields
#        except AttributeError:
#            pass  # No aliases for this part.
        
        hash_fields = {k: fields[k] for k in fields if k not in ('manf#','manf') and SEPRTR not in k}
        h = hash(tuple(sorted(hash_fields.items())))
        
        component_groups[h] = IdenticalComponents()  # Add empty structure.
        component_groups[h].fields = fields
#        component_groups[h].refs = p['designator1'].replace(' ','').split(',')  # Init list of refs with first ref.
        # Now add the manf. part num (or None) for this part to the group set.
        component_groups[h].manf_nums = set([fields.get('manf#')])
        
    # Now we have groups of seemingly identical parts. But some of the parts
    # within a group may have different manufacturer's part numbers, and these
    # groups may need to be split into smaller groups of parts all having the
    # same manufacturer's number. Here are the cases that need to be handled:
    #   One manf# number: All parts have the same manf#. Don't split this group.
    #   Two manf# numbers, but one is None: Some of the parts have no manf# but
    #       are otherwise identical to the other parts in the group. Don't split
    #       this group. Instead, propagate the non-None manf# to all the parts.
    #   Two manf#, neither is None: All parts have non-None manf# numbers.
    #       Split the group into two smaller groups of parts all having the same
    #       manf#.
    #   Three or more manf#: Split this group into smaller groups, each one with
    #       parts having the same manf#, even if it's None. It's impossible to
    #       determine which manf# the None parts should be assigned to, so leave
    #       their manf# as None.
    new_component_groups = [] # Copy new component groups into this.
    for g, grp in list(component_groups.items()):
        num_manf_nums = len(grp.manf_nums)
        if num_manf_nums == 1:
            new_component_groups.append(grp)
            continue  # Single manf#. Don't split this group.
        elif num_manf_nums == 2 and None in grp.manf_nums:
            new_component_groups.append(grp)
            continue  # Two manf#, but one of them is None. Don't split this group.
        # Otherwise, split the group into subgroups, each with the same manf#.
        for manf_num in grp.manf_nums:
            sub_group = IdenticalComponents()
            sub_group.manf_nums = [manf_num]
            sub_group.refs = []
            for ref in grp.refs:
                # Use get() which returns None if the component has no manf# field.
                # That will match if the group manf_num is also None.
                if components[ref].get('manf#') == manf_num:
                    sub_group.refs.append(ref)
            new_component_groups.append(sub_group)
    
    prj_info = {'title':'No title','company':'No company founded'} # Information not avaliable.

    # Now return the list of identical part groups.
    return new_component_groups, prj_info

if __name__=='__main__':
    print('\n\n\n############## File 1\n')
    file_handle = open('Bill Of Materials board.csv')
    parts,prj_info = get_part_groups_generic_csv(file_handle,'','')
    print(parts,prj_info)
    print('\n\n\n############## File 2\n')
    file_handle = open('generic_BOM_example.csv')
    parts,prj_info = get_part_groups_generic_csv(file_handle,'','')
    print(parts,prj_info)
