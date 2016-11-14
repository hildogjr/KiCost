# Inserted by Pasteurize tool.
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from builtins import zip
from builtins import range
from builtins import int
from builtins import str
from future import standard_library
standard_library.install_aliases()

import future

from bs4 import BeautifulSoup
import logging

logger = logging.getLogger('kicost')

DEBUG_OVERVIEW = logging.DEBUG
DEBUG_DETAILED = logging.DEBUG-1
DEBUG_OBSESSIVE = logging.DEBUG-2

import sys

SEPRTR = ':'  # Delimiter between library:component, distributor:field, etc.

# Temporary class for storing part group information.
class IdenticalComponents(object):
    pass

def get_part_groups_altium(in_file, ignore_fields, variant):
    '''Get groups of identical parts from an XML file and return them as a dictionary.'''

    ign_fields = [str(f.lower()) for f in ignore_fields]
    

    def extract_fields(part, variant):
        '''Extract XML fields from the part in a library or schematic.'''        

        fields = {}
        
        if sys.version[0]=='2':
            fields['footprint']=part['footprint1'].encode('ascii', 'ignore')
            fields['libpart']=part['libref1'].encode('ascii', 'ignore')
            fields['value']=part['value3'].encode('ascii', 'ignore')
            fields['reference']=part['comment1'].encode('ascii', 'ignore')
            fields['manf#']=part['manufacturer_part_number_11'].encode('ascii', 'ignore')
        else:            
            fields['footprint']=part['footprint1']
            fields['libpart']=part['libref1']
            fields['value']=part['value3']
            fields['reference']=part['comment1']
            fields['manf#']=part['manufacturer_part_number_11']
                
        return fields

    # Read-in the schematic XML file to get a tree and get its root.
    logger.log(DEBUG_OVERVIEW, 'Get schematic XML...')
    root = BeautifulSoup(in_file, 'lxml')
    
    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    logger.log(DEBUG_OVERVIEW, 'Get parts library...')
    libparts = {}
    component_groups = {}
    
    for p in root.find('rows').find_all('row'):
					
        # Get the values for the fields in each library part (if any).
        fields = extract_fields(p, variant)

        # Store the field dict under the key made from the
        # concatenation of the library and part names.
        #~ libparts[str(fields['libpart'] + SEPRTR + fields['reference'])] = fields
        libparts[fields['libpart'] + SEPRTR + fields['reference']] = fields
        
        # Also have to store the fields under any part aliases.
        try:
            for alias in p.find('aliases').find_all('alias'):
                libparts[str(fields['libpart'] + SEPRTR + alias.string)] = fields
        except AttributeError:
            pass  # No aliases for this part.
        
        hash_fields = {k: fields[k] for k in fields if k not in ('manf#','manf') and SEPRTR not in k}
        h = hash(tuple(sorted(hash_fields.items())))
        
        component_groups[h] = IdenticalComponents()  # Add empty structure.
        component_groups[h].fields = fields
        component_groups[h].refs = p['designator1'].replace(' ','').split(',')  # Init list of refs with first ref.
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

    # Now return the list of identical part groups.
    return new_component_groups

    
    # Now return a list of the groups without their hash keys.
    return list(new_component_groups.values())

if __name__=='__main__':
	
	file_handle=open('meacs.xml')
	#~ file_handle=open('wiSensAFE.xml')
	
	get_part_groups_altium(file_handle,'','')
