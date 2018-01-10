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
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'
# This module is intended to work with Altium XML files.

# Libraries.
from sys import version_info as python_version
from bs4 import BeautifulSoup # To Read XML files.
import re # Regular expression parser.
import logging
from ...kicost import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE # Debug configurations.
from ...kicost import distributors, SEPRTR
from ..eda_tools import field_name_translations, subpart_split, group_parts, split_refs

# Add to deal with the fileds of Altium and WEB tools.
field_name_translations.update(
    {
        'designator': 'refs',
        'quantity': 'qty',
        'manufacturer name': 'manf', # Used for some web site tools to part generator in Altium.
        'manufacturer part number': 'manf#'
    }
)

ALTIUM_NONE = '[NoParam]' # Value of Altium to a not setted param.
ALTIUM_PART_SEPRTR = r'(?<!\\)\s*[,]\s*' # Separator for the part numbers in a list, remove the lateral spaces.

#TODO
# - No geral, executar `group_parts` no arquivo `kicost.py`, depois do loop de ler vários arquivos. Isso agruparão partes entre eles (retirar a chamada e comentário de dentro de `kicad.py`e `generic_csv.py`
# - Mover funções de web para fora de `kicost.py`


def get_part_groups(in_file, ignore_fields, variant):
    '''Get groups of identical parts from an XML file and return them as a dictionary.'''

    ign_fields = [str(f.lower()) for f in ignore_fields]
    

    def extract_field(xml_entry, field_name):
        '''Extract XML fields from XML entry given.'''
        try:
            if python_version>=(3,0):
                return xml_entry[field_name]
            else:
                return xml_entry[field_name].encode('ascii', 'ignore')
        except KeyError:
            return None

    def extract_fields(part, variant):
        '''Extract XML fields from the part in a library or schematic.'''
        fields = {}
        for h in header:
            value = extract_field(part, h)
            if value and value!=ALTIUM_NONE:
                fields[field_name_translations.get(hdr.lower(),hdr.lower())] = value
        return fields

    # Read-in the schematic XML file to get a tree and get its root.
    logger.log(DEBUG_OVERVIEW, 'Get schematic XML...')
    root = BeautifulSoup(in_file, 'lxml')
    
    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    logger.log(DEBUG_OVERVIEW, 'Get parts library...')
    libparts = {}
    component_groups = {}
    
    # Get the header of the XML file of Altium, so KiCost is able to to
    # to get all the informations in the file.
    header = [ extract_field(entry, 'name') for entry in root.find('columns').find_all('column') ]
    
    for p in root.find('rows').find_all('row'):

        # Get the values for the fields in each library part (if any).
        fields = extract_fields(p, variant)
        
        print(fileds)
        
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

    # Altium XML file don't have project general information.
    prj_info = {'title':'No title','company':'Not avaliable','date':'Not avaliable'}

    # Now return the list of identical part groups.
    return new_component_groups, prj_info
