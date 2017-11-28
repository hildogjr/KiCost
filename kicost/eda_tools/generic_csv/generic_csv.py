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
from ..eda_tools import field_name_translations
from ..eda_tools import subpart_split

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

GENERIC_REF = 'generic' # Generic text reference to components.

# Temporary class for storing part group information.
class IdenticalComponents(object):
    pass

def get_part_groups(in_file, ignore_fields, variant):
    '''Get groups of identical parts from an generic CSV file and return them as a dictionary.'''
    # No `variant` of ignore field is used in this function, the input is just kept by compatibily.
    # Enven not `ignore_filds` to be ignored.
    
    logger.log(DEBUG_OVERVIEW, 'Get schematic CSV...')
    content = in_file.read()
    in_file.close()
    
    # Try to get the dialect, sometimes differents OS and languages of
    # than put differents delimiters to the values in a CSV file.
    content = re.sub('\t+', '\t', content) # Remove extra '\t' that migth be used by users
                                           # to write hand CSV in text editors.
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
    
    prj_info = {'title':'No title','company':'Not avaliable','date':'Not avaliable'} # Information not avaliable.
    
    # Local function defined to get the conrrespondence fileds from the CSV file.
    def extract_fields(text):
        '''Extract the correspondence fields in the CSV lines.'''
        extract_fields.count_generic_ref += 1 # Counter of the generics reference.
        fields = {}
        values = next(csv.reader([text.replace("'",'"')],delimiter=dialect.delimiter))
        # Default text to some fields needed for KiCost.
        fields['libpart'] = 'Lib:Cat'
        fields['footprint'] = 'Cat:Fooprint'
        fields['value'] = 'Not assined' # Value of the component.
        fields['refs'] = 'generic' # Letter used to identify groups of components.
        refs = GENERIC_REF + '{}'.format(extract_fields.count_generic_ref)
        fields['refs'] =  'generic'
        for iV in range(len(values)):
            if header[iV] == 'refs':
                ref = values[iV]
                if ref=='':
                    # Enunciated the reference but empty.
                    fields['refs'] = GENERIC_REF
                    refs = split_refs (GENERIC_REF + 
                                       '{1}-{2}'.format(
                                          extract_fields.count_generic_ref,
                                          extract_fields.count_generic_ref+values['qty']-1
                                       )
                                      )
                    extract_fields.count_generic_ref += values['qty'] -1
                refs = split_refs(ref)
                fields['refs'] = re.findall('^\D+', refs[0])[0] # Recognize the letter(s) of the grups.
            elif header[iV] == 'qty' and not 'refs' in header:
                # Enunciated the quantity but not the references.
                fields['refs'] = GENERIC_REF
                refs = split_refs (GENERIC_REF + 
                                   '{1}-{2}'.format(
                                      extract_fields.count_generic_ref,
                                      extract_fields.count_generic_ref+values['qty']-1
                                   )
                                  )
                extract_fields.count_generic_ref += values['qty'] -1
            else:
                fields[header[iV]] = values[iV]
        return refs, fields
    extract_fields.count_generic_ref = 0
    
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
    
    # Replace the component list with the list of accepted parts.
    components = subpart_split(accepted_components)
    print(components)

    # Now partition the parts into groups of like components.
    # First, get groups of identical components but ignore any manufacturer's
    # part numbers that may be assigned. Just collect those in a list for each group.
    logger.log(DEBUG_OVERVIEW, 'Get groups of identical components...')
    component_groups = {}
    for ref, fields in list(components.items()): # part references and field values.

        # Take the field keys and values of each part and create a hash.
        # Use the hash as the key to a dictionary that stores lists of
        # part references that have identical field values. The important fields
        # are the reference prefix ('R', 'C', etc.), value, and footprint.
        # Don't use the manufacturer's part number when calculating the hash!
        # Also, don't use any fields with SEPRTR in the label because that indicates
        # a field used by a specific tool (including kicost).
        hash_fields = {k: fields[k] for k in fields if k not in ('manf#','manf') and SEPRTR not in k}
        h = hash(tuple(sorted(hash_fields.items())))

        # Now add the hashed component to the group with the matching hash
        # or create a new group if the hash hasn't been seen before.
        try:
            # Add next ref for identical part to the list.
            component_groups[h].refs.append(ref)
            # Also add any manufacturer's part number (or None) to the group's list.
            component_groups[h].manf_nums.add(fields.get('manf#'))
        except KeyError:
            # This happens if it is the first part in a group, so the group
            # doesn't exist yet.
            component_groups[h] = IdenticalComponents()  # Add empty structure.
            component_groups[h].refs = [ref]  # Init list of refs with first ref.
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

    # Now get the values of all fields within the members of a group.
    # These will become the field values for ALL members of that group.
    for grp in new_component_groups:
        grp_fields = {}
        for ref in grp.refs:
            for key, val in list(components[ref].items()):
                if val is None: # Field with no value...
                    continue # so ignore it.
                if grp_fields.get(key): # This field has been seen before.
                    if grp_fields[key] != val: # Flag if new field value not the same as old.
                        raise Exception('field value mismatch: {} {} {}'.format(ref, key, val))
                else: # First time this field has been seen in the group, so store it.
                    grp_fields[key] = val
        grp.fields = grp_fields

    # Now return the list of identical part groups.
    return new_component_groups, prj_info



# --------------- Local functions.

def split_refs(text):
    '''Split string grouped references into a unique designator.'''
    # 'C17/18/19/20' --> ['C17','C18','C19','C20']
    # 'C17\18\19\20' --> ['C17','C18','C19','C20']
    # 'D33-D36' --> ['D33','D34','D35','D36']
    # 'D33-36' --> ['D33','D34','D35','D36']
    # Also ignore some caracheters as '.' or ':' used in some cases of references.
    partial_ref = re.split('[,;]', text)
    refs = []
    for ref in partial_ref:
        # Remove invalid characters.
        ref = re.sub('\+$', 'p', ref) # Finishin "+".
        ref = re.sub('[\+\s\_\.\(\)\$\*]', '', ref) # Generic special caracheters.
        ref = re.sub('\-+', '-', ref) # Double "-".
        ref = re.sub('^\-', '', ref) # Stating "-".
        ref = re.sub('\-$', 'n', ref) # Finishin "-".
        if re.search('^\w+\d', ref):
            if re.search('-', ref):
                designator_name = re.findall('^\D+', ref)[0]
                splitted_nums = re.split('-', ref)
                designator_name += ''.join( re.findall('^d*\W', splitted_nums[0] ) )
                splitted_nums = [re.sub(designator_name,'',splitted_nums[i]) for i in range(len(splitted_nums))]
                splitted = list( range( int(splitted_nums[0]), int(splitted_nums[1])+1 ) )
                splitted = [designator_name+str(splitted[i]) for i in range(len(splitted)) ]
                refs += splitted
            elif re.search('[/\\\]', ref):
                designator_name = re.findall('^\D+',ref)[0]
                splitted_nums = [re.sub('^'+designator_name, '', i) for i in re.split('[/\\\]',ref)]
                refs += [designator_name+i for i in splitted_nums]
            else:
                refs += [ref]
        else:
            # The designator name is not for a group of components and 
            # "\", "/" or "-" ir part of the name. This characters have
            # to be removed.
            ref = re.sub('[\-\/\\\]', '', ref)
            refs += [ref]
    return refs

if __name__=='__main__':
    print('\n\n\n############## File 1\n')
    file_handle = open('Bill Of Materials board.csv')
    parts,prj_info = get_part_groups_generic_csv(file_handle,'','')
    print(parts,prj_info)
    print('\n\n\n############## File 2\n')
    file_handle = open('generic_BOM_example.csv')
    parts,prj_info = get_part_groups_generic_csv(file_handle,'','')
    print(parts,prj_info)
