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
# This module is intended to work with Altium XML files.

# Libraries.
import sys
import os
import copy  # Necessary because Py2 doesn't have copy in list.
from datetime import datetime
from bs4 import BeautifulSoup  # To Read XML files.
import re  # Regular expression parser.
from .tools import field_name_translations, PART_REF_REGEX_NOT_ALLOWED
from .eda import eda_class
from .log__ import debug_overview
from .. import KiCostError, ERR_INPUTFILE

ALTIUM_NONE = '[NoParam]'  # Value of Altium to `None`.
ALTIUM_PART_SEPRTR = r'(?<!\\),\s*'  # Separator for the part numbers in a list, remove the lateral spaces.
FILE_REGEX = r'\<GRID[\s\S]+<COLUMNS>[\s\S]+<COLUMN[\s\S]+<\/COLUMNS>[\s\S]+<ROWS>[\s\S]+\<ROW[\s\S]+\<\/ROWS>[\s\S]+\<\/GRID>'

__all__ = ['eda_altium']


def extract_field(xml_entry, field_name):
    '''Extract XML fields from XML entry given.'''
    try:
        if sys.version_info >= (3, 0):
            return xml_entry[field_name]
        else:
            return xml_entry[field_name].encode('ascii', 'ignore')
    except KeyError:
        return None


def extract_fields_row(row, header):
    '''Extract XML fields from the part in a library or schematic.'''

    # First get the references and the quantities of elements in each row group.
    header_translated = [field_name_translations.get(hdr.lower(), hdr.lower()) for hdr in header]
    hdr_refs = [i for i, x in enumerate(header_translated) if x == "refs"]
    if not hdr_refs:
        raise KiCostError('No part designators/references found in the BOM.\nTry to generate the file again with Altium.', ERR_INPUTFILE)
    else:
        hdr_refs = hdr_refs[0]
    refs = re.split(ALTIUM_PART_SEPRTR, extract_field(row, header[hdr_refs].lower()))
    header_valid = copy.copy(header)
    header_valid.remove(header[hdr_refs])
    try:
        hdr_qty = [i for i, x in enumerate(header_translated) if x == "qty"][0]
        qty = int(extract_field(row, header[hdr_qty].lower()))
        header_valid.remove(header[hdr_qty])
        if qty != len(refs):
            raise KiCostError('Not recognize the division elements in the Altium BOM.\nIf you are using subparts, try to replace the separator from `, `'
                              ' to `,` or better, use `;` instead `,`.', ERR_INPUTFILE)
    except Exception:
        qty = len(refs)

    # After the others fields.
    fields = [dict() for x in range(qty)]
    for hdr in header_valid:
        # Extract each information, by the the header given, for each row part, spliting it in a list.
        value = extract_field(row, hdr.lower())
        value = re.split(ALTIUM_PART_SEPRTR, value)
        for i in range(qty):
            if len(value) == qty:
                v = value[i]
            else:
                v = value[0]  # Footprint is just one for group.
            fields[i][field_name_translations.get(hdr.lower(), hdr.lower())] = v
    return refs, fields


def get_part_groups(in_file):
    '''@brief Get groups of identical parts from an XML file and return them as a dictionary.
       @param in_file `str()` with the file name.
       @return `dict()` of the parts designed. The keys are the componentes references.
    '''
    # Read-in the schematic XML file to get a tree and get its root.
    debug_overview('# Getting from XML \'{}\' Altium BoM...'.format(
                                    os.path.basename(in_file)))
    file_h = open(in_file)
    root = BeautifulSoup(file_h, 'lxml')
    file_h.close()

    # Get the header of the XML file of Altium, so KiCost is able to to
    # to get all the informations in the file.
    debug_overview('Getting the XML table header...')
    header = [extract_field(entry, 'name') for entry in root.find('columns').find_all('column')]

    debug_overview('Getting components...')
    accepted_components = {}
    for row in root.find('rows').find_all('row'):

        # Get the values for the fields in each library part (if any).
        refs, fields = extract_fields_row(row, header)
        for i in range(len(refs)):
            ref = refs[i]
            ref = re.sub(r'\+$', 'p', ref)  # Finishing "+".
            ref = re.sub(PART_REF_REGEX_NOT_ALLOWED, '', ref)  # Generic special characters not allowed. To work around #ISSUE #89.
            ref = re.sub(r'\-+', '-', ref)  # Double "-".
            ref = re.sub(r'^\-', '', ref)  # Starting "-".
            ref = re.sub(r'\-$', 'n', ref)  # Finishing "-".
            if not re.search(r'\d$', ref):
                ref += '0'
            accepted_components[re.sub(PART_REF_REGEX_NOT_ALLOWED, '', ref)] = fields[i]

    # Not founded project information at the file content.
    prj_info = {'title': os.path.basename(in_file),
                'company': None,
                'date': datetime.fromtimestamp(os.path.getmtime(in_file)).strftime("%Y-%m-%d %H:%M:%S") + ' (file)'}

    return accepted_components, prj_info


class eda_altium(eda_class):
    name = 'altium'
    label = 'Altium file'  # Label used on the GUI.
    desc = 'Altium Limited (formerly known as Protel until 2001).'

    @staticmethod
    def get_part_groups(in_file, distributors):
        return get_part_groups(in_file)

    @staticmethod
    def file_eda_match(content, extension):
        ''' Returns True if this EDA can handle this file. '''
        return extension == '.xml' and re.search(FILE_REGEX, content, re.IGNORECASE)


eda_class.register(eda_altium)
