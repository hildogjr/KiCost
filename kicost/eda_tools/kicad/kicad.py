# MIT license
#
# Copyright (C) 2018 by XESS Corporation
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

import sys, os, time
import re
from bs4 import BeautifulSoup
from ...globals import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE
from ...globals import SEPRTR
from ...kicost import distributor_dict
from ..eda_tools import field_name_translations


def get_part_groups(in_file, ignore_fields, variant):
    '''Get groups of identical parts from an XML file and return them as a dictionary.'''

    ign_fields = [str(f.lower()) for f in ignore_fields]

    def extract_fields(part, variant):
        # Extract XML fields from the part in a library or schematic.

        fields = {}
        try:
            for f in part.find('fields').find_all('field'):
                # Store the name and value for each kicost-related field.
                # Remove case of field name along with leading/trailing whitespace.
                name = str(f['name']).lower().strip()
                if name in ign_fields:
                    continue  # Ignore fields in the ignore list.
                elif SEPRTR not in name: # No separator, so get global field value.
                    name = field_name_translations.get(name, name)
                    value = str(f.string)
                    if value:
                        fields[name] = value # Do not create empty fields. This is usefull
                                             # when used more than one `manf#` alias in one designator.
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
                        value = str(f.string)
                        if value:
                            fields[name] = value

        except AttributeError:
            pass  # No fields found for this part.
        return fields

    # Read-in the schematic XML file to get a tree and get its root.
    logger.log(DEBUG_OVERVIEW, 'Get schematic XML...')
    file_h = open(in_file)
    root = BeautifulSoup(file_h, 'lxml')
    file_h.close()

    # Get the general information of the project BoM XML file.
    title = root.find('title_block')
    def title_find_all(data, field):
        '''Helper function for finding title info, especially if it is absent.'''
        try:
            return data.find_all(field)[0].string
        except (AttributeError, IndexError):
            return None
    prj_info = dict()
    prj_info['title'] = title_find_all(title, 'title') or os.path.basename( in_file )
    prj_info['company'] = title_find_all(title, 'company')
    prj_info['date'] = title_find_all(root, 'date') or (time.ctime(os.path.getmtime(in_file)) + ' (file)')

    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    logger.log(DEBUG_OVERVIEW, 'Get parts library...')
    libparts = {}
    if root.find('libparts'):
        for p in root.find('libparts').find_all('libpart'):

            # Get the values for the fields in each library part (if any).
            fields = extract_fields(p, variant)

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
    logger.log(DEBUG_OVERVIEW, 'Get components...')
    components = {}
    for c in root.find('components').find_all('comp'):

        # Find the library used for this component.
        libsource = c.find('libsource')

        # Create the key to look up the part in the libparts dict.
        #libpart = str(libsource['lib'] + SEPRTR + libsource['part'])
        libpart = str(libsource['lib']) + SEPRTR + str(libsource['part'])

        # Initialize the fields from the global values in the libparts dict entry.
        # (These will get overwritten by any local values down below.)
        # (Use an empty dict if no part exists in the library.)
        fields = libparts.get(libpart, dict()).copy() # Make a copy! Don't use reference!

        # Store the part key and its value.
        fields['libpart'] = libpart
        fields['value'] = str(c.find('value').string)

        # Get the footprint for the part (if any) from the schematic.
        try:
            fields['footprint'] = str(c.find('footprint').string)
        except AttributeError:
            pass

        # Get the values for any other kicost-related fields in the part
        # (if any) from the schematic. These will override any field values
        # from the part library.
        fields.update(extract_fields(c, variant))

        # Store the fields for the part using the reference identifier as the key.
        components[str(c['ref'])] = fields

    # Remove components that are assigned to a variant that is not the current variant,
    # or which are "do not popoulate" (DNP). (Any component that does not have a variant
    # is assigned the current variant so it will not be removed unless it is also DNP.)
    accepted_components = {}
    for ref, fields in components.items():
        # Remove DNPs.
        dnp = fields.get('local:dnp', fields.get('dnp', 0))
        try:
            dnp = float(dnp)
        except ValueError:
            pass  # The field value must have been a string.
        if dnp:
            continue

        # Get part variant. Prioritize local variants over global ones.
        variants = fields.get('local:variant', fields.get('variant', None))

        # Remove parts that are not assigned to the current variant.
        # If a part is not assigned to any variant, then it is never removed.
        if variants:
            # A part can be assigned to multiple variants. The part will not
            # be removed if any of its variants match the current variant.
            # Split the variants apart and abort the loop if any of them match.
            for v in re.split('[,;/ ]', variants):
                if re.match(variant, v, flags=re.IGNORECASE):
                    break
            else:
                # None of the variants matched, so skip/remove this part.
                continue

        # The part was not removed, so add it to the list of accepted components.
        accepted_components[ref] = fields

    return accepted_components, prj_info
