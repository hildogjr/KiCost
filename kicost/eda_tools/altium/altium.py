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
import sys, os, time
from datetime import datetime
from bs4 import BeautifulSoup # To Read XML files.
import re # Regular expression parser.
import logging
from ...globals import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE # Debug configurations.
from ...globals import SEPRTR
from ...kicost import distributor_dict
from ..eda_tools import field_name_translations, remove_dnp_parts
from ..eda_tools import PART_REF_REGEX_NOT_ALLOWED

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


def get_part_groups(in_file, ignore_fields, variant):
    '''@brief Get groups of identical parts from an XML file and return them as a dictionary.
       @param in_file `str()` with the file name.
       @param ignore_fields `list()` fields do be ignored on the read action.
       @param variant `str()` in regular expression to match with the design version of the BOM.
       @return `dict()` of the parts designed. The keys are the componentes references.
    '''

    ign_fields = [str(f.lower()) for f in ignore_fields]

    def extract_field(xml_entry, field_name):
        '''Extract XML fields from XML entry given.'''
        try:
            if sys.version_info>=(3,0):
                return xml_entry[field_name]
            else:
                return xml_entry[field_name].encode('ascii', 'ignore')
        except KeyError:
            return None

    def extract_fields_row(row, variant):
        '''Extract XML fields from the part in a library or schematic.'''
        
        # First get the references and the quantities of elements in each rwo group.
        header_translated = [field_name_translations.get(hdr.lower(),hdr.lower()) for hdr in header]
        hdr_refs = [i for i, x in enumerate(header_translated) if x == "refs"]
        if not hdr_refs:
            sys.exit('Not founded the part designators/references in the BOM.\nTry to generate the file again at Altium.')
        else:
            hdr_refs = hdr_refs[0]
        refs = re.split(ALTIUM_PART_SEPRTR, extract_field(row, header[hdr_refs].lower()) )
        header_valid = header.copy()
        header_valid.remove(header[hdr_refs])
        try:
            hdr_qty = [i for i, x in enumerate(header_translated) if x == "qty"][0]
            qty = int( extract_field(row, header[hdr_qty].lower()) )
            header_valid.remove(header[hdr_qty])
            if qty!=len(refs):
                sys.exit('Not recognize the division elements in the Altium BOM.\nIf you are using subparts, try to replace the separator from `, ` to `,` or better, use `;` instead `,`.')
        except:
            qty = len(refs)
        
        # After the others fields.
        fields = [dict() for x in range(qty)]
        for hdr in header_valid:
            # Extract each information, by the the header given, for each
            # row part, spliting it in a list.
            value = extract_field(row, hdr.lower())
            value = re.split(ALTIUM_PART_SEPRTR, value)
            if hdr.lower() in ign_fields:
                continue
            elif not SEPRTR in hdr.lower():
                for i in range(qty):
                    if len(value)==qty:
                        v = value[i]
                    else:
                        v = value[0] # Footprint is just one for group.
                    # Do not create empty fields. This is useful
                    # when used more than one `manf#` alias in one designator.
                    if v and v!=ALTIUM_NONE:
                        fields[i][field_name_translations.get(hdr.lower(),hdr.lower())] = v.strip()
            else:
                # Now look for fields that start with 'kicost' and possibly
                # another dot-separated variant field and store their values.
                # Anything else is in a non-kicost namespace.
                key_re = 'kicost(\.{})?:(?P<name>.*)'.format(variant)
                mtch = re.match(key_re, name, flags=re.IGNORECASE)
                if mtch:
                    # The field name is anything that came after the leading
                    # 'kicost' and variant field.
                    name = mtch.group('name')
                    name = field_name_translations.get(name, name)
                    # If the field name isn't for a manufacturer's part
                    # number or a distributors catalog number, then add
                    # it to 'local' if it doesn't start with a distributor
                    # name and colon.
                    if name not in ('manf#', 'manf') and name[:-1] not in distributor_dict:
                        if SEPRTR not in name: # This field has no distributor.
                            name = 'local:' + name # Assign it to a local distributor.
                    for i in range(qty):
                        if len(value)==qty:
                            v = value[i]
                        else:
                            v = value[0] # Footprint is just one for group.
                        # Do not create empty fields. This is useful
                        # when used more than one `manf#` alias in one designator.
                        if v and v!=ALTIUM_NONE:
                            fields[i][field_name_translations.get(hdr.lower(),hdr.lower())] = v.strip()
        return refs, fields

    # Read-in the schematic XML file to get a tree and get its root.
    logger.log(DEBUG_OVERVIEW, 'Getting from XML \'{}\' Altium BoM...'.format(
                                    os.path.basename(in_file)) )
    file_h = open(in_file)
    root = BeautifulSoup(file_h, 'lxml')
    file_h.close()

    # Get the header of the XML file of Altium, so KiCost is able to to
    # to get all the informations in the file.
    logger.log(DEBUG_OVERVIEW, '\tGetting the XML table header...')
    header = [ extract_field(entry, 'name') for entry in root.find('columns').find_all('column') ]

    logger.log(DEBUG_OVERVIEW, '\tGetting components...')
    accepted_components = {}
    for row in root.find('rows').find_all('row'):

        # Get the values for the fields in each library part (if any).
        refs, fields = extract_fields_row(row, variant)
        for i in range(len(refs)):
            ref = refs[i]
            ref = re.sub('\+$', 'p', ref) # Finishing "+".
            ref = re.sub(PART_REF_REGEX_NOT_ALLOWED, '', ref) # Generic special characters not allowed. To work around #ISSUE #89.
            ref = re.sub('\-+', '-', ref) # Double "-".
            ref = re.sub('^\-', '', ref) # Starting "-".
            ref = re.sub('\-$', 'n', ref) # Finishing "-".
            if not re.search('\d$', ref):
                ref += '0'
            accepted_components[ re.sub(PART_REF_REGEX_NOT_ALLOWED, '', ref) ] = fields[i]

    # Not founded project information at the file content.
    prj_info = {'title': os.path.basename( in_file ),
                'company': None,
                'date': datetime.strptime(time.ctime(os.path.getmtime(in_file)), '%a %b %d %H:%M:%S %Y').strftime("%Y-%m-%d %H:%M:%S") + ' (file)'}

    return remove_dnp_parts(accepted_components, variant), prj_info
