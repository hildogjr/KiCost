# -*- coding: utf-8 -*-

# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Junior
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

# Libraries.
import os
from datetime import datetime
import re
from bs4 import BeautifulSoup
from collections import OrderedDict
from .. import SEPRTR
from .eda import eda_class
from .log__ import debug_overview


__all__ = ['eda_kicad']


def extract_fields(part):
    ''' Extract XML fields from the part in a library or schematic. '''
    # Here the order of the dict is important
    # The fields from the library must be easily redefined by the component
    fields = OrderedDict()
    try:
        for f in part.find('fields').find_all('field'):
            name = str(f['name'])
            if name == 'Reference':
                # Excluded to avoid problems to group parts of differents sheets ISSUE #97.
                continue
            # Store the name and value for each kicost-related field.
            # Remove case of field name along with leading/trailing whitespace.
            # Note: str() is needed to avoid Python 2.7 then printing it as u'xxx'
            fields[name] = str(f.string) if f.string is not None else ''
    except AttributeError:
        pass  # No fields found for this part.
    return fields


def title_find_all(data, field):
    ''' Helper function for finding title info, especially if it is absent. '''
    try:
        return data.find_all(field)[0].string
    except (AttributeError, IndexError):
        return None


def get_part_groups(in_file):
    '''Get groups of identical parts from an XML file and return them as a dictionary.
       @param in_file `str()` with the file name.
       @return `dict()` of the parts designed. The keys are the componentes references.
    '''
    # Read-in the schematic XML file to get a tree and get its root.
    debug_overview('# Getting from XML \'{}\' KiCad BoM...'.format(
                                    os.path.basename(in_file)))
    file_h = open(in_file)
    root = BeautifulSoup(file_h, 'lxml')
    file_h.close()

    # Get the general information of the project BoM XML file.
    debug_overview('Getting authorship data...')
    title = root.find('title_block')

    prj_info = dict()
    prj_info['title'] = title_find_all(title, 'title') or os.path.basename(in_file)
    prj_info['company'] = title_find_all(title, 'company')
    prj_info['date'] = title_find_all(root, 'date') or (datetime.fromtimestamp(os.path.getmtime(in_file)).strftime("%Y-%m-%d %H:%M:%S") + ' (file)')

    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    debug_overview('Getting parts library...')
    libparts = {}
    if root.find('libparts'):
        for p in root.find('libparts').find_all('libpart'):

            # Get the values for the fields in each library part (if any).
            fields = extract_fields(p)

            # Store the field dict under the key made from the
            # concatenation of the library and part names.
            libparts[str(p['lib']) + SEPRTR + str(p['part'])] = fields

            # Also have to store the fields under any part aliases.
            try:
                for alias in p.find('aliases').find_all('alias'):
                    libparts[str(p['lib']) + SEPRTR + str(alias.string)] = fields
            except AttributeError:
                pass  # No aliases for this part.

    # Find the components used in the schematic and elaborate
    # them with global values from the libraries and local values
    # from the schematic.
    debug_overview('Getting components...')
    components = OrderedDict()
    for c in root.find('components').find_all('comp'):

        # Find the library used for this component.
        libsource = c.find('libsource')
        if libsource:
            # Create the key to look up the part in the libparts dict.
            # libpart = str(libsource['lib'] + SEPRTR + libsource['part'])
            libpart = str(libsource['lib']) + SEPRTR + str(libsource['part'])
        else:
            libpart = '???'
            debug_overview('Footprint library not assigned to {}'.format(''))  # TODO

        # Initialize the fields from the global values in the libparts dict entry.
        # (These will get overwritten by any local values down below.)
        # (Use an empty dict if no part exists in the library.)
        fields = libparts.get(libpart, OrderedDict()).copy()  # Make a copy! Don't use reference!

        # Store the part key and its value.
        fields['libpart'] = libpart

        # Get the footprint for the part (if any) from the schematic.
        try:
            fields['Value'] = str(c.find('value').string)
            fields['Footprint'] = str(c.find('footprint').string)
            fields['Datasheet'] = str(c.find('datasheet').string)
        except AttributeError:
            pass

        # Get the values for any other kicost-related fields in the part
        # (if any) from the schematic. These will override any field values
        # from the part library.
        fields.update(extract_fields(c))

        # Store the fields for the part using the reference identifier as the key.
        components[str(c['ref'])] = fields

    return components, prj_info


class eda_kicad(eda_class):
    name = 'kicad'
    label = 'KiCad file'  # Label used on the GUI.
    desc = 'KiCad open source EDA.'

    @staticmethod
    def get_part_groups(in_file, distributors):
        return get_part_groups(in_file)

    @staticmethod
    def file_eda_match(content, extension):
        ''' Returns True if this EDA can handle this file. '''
        return extension == '.xml' and re.search(r'<tool\>Eeschema.*\<\/tool\>', content, re.IGNORECASE)


eda_class.register(eda_kicad)
