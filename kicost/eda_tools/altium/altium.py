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

ALTIUM_NONE = '[NoParam]' # Value of Altium to `None`.
ALTIUM_PART_SEPRTR = r'(?<!\\),\s*' # Separator for the part numbers in a list, remove the lateral spaces.

#TODO
# - No geral, executar `group_parts` no arquivo `kicost.py`, depois do lo, op de ler vários arquivos. Isso agruparão partes entre eles (retirar a chamada e comentário de dentro de `kicad.py`e `generic_csv.py`
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

    def extract_fields_row(part, variant):
        '''Extract XML fields from the part in a library or schematic.'''
        fields = {}
        for hdr in header:
            # Extract each information, by the the header given, for each
            # row part, spliting it in a list.
            value = extract_field(part, hdr.lower())
            value = re.split(ALTIUM_PART_SEPRTR, value)
            
            if not hdr.lower() in ign_fields:
                for v in value:
                    if field_name_translations.get(hdr.lower(),hdr.lower()) != 'refs':
                        refs = value
                    else:
                        # Do not create empty fields. This is userfull
                        # when used more than one `manf#` alias in one designator.
                        if v and v!=ALTIUM_NONE:
                            fields[field_name_translations.get(hdr.lower(),hdr.lower())] = v.strip()
        return refs, fields

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
        fields = extract_fields_row(p, variant)
        
        refs, fields = extract_fields(row)
        for ref in refs:
           accepted_components[ref] = fields

    # Altium XML file don't have project general information.
    prj_info = {'title':'No title','company':'Not avaliable','date':'Not avaliable'}

    # Now return the list of identical part groups.
    return accepted_components, prj_info
