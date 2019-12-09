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
import sys, os, time
from datetime import datetime
import re
from bs4 import BeautifulSoup
from ..global_vars import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE
from ..global_vars import SEPRTR
from ..distributors.global_vars import distributor_dict
from .tools import field_name_translations, remove_dnp_parts


__all__ = ['get_part_groups']

from . import eda_dict

# Place information about this EDA into the eda_tool dictionary.
eda_dict.update(
    {
        'kicad': {
            'module': 'kicad', # The directory name containing this file.
            'label': 'KiCad file', # Label used on the GUI.
            'desc': 'KiCad open source EDA.',
            # Formatting file match.
            'file': {
                'extension': '.xml', # File extension.
                'content': '<tool\>Eeschema.*\<\/tool\>' # Regular expression content match.
                }
        }
    }
)

def get_part_groups(in_file, ignore_fields, variant):
    '''Get groups of identical parts from an XML file and return them as a dictionary.
       @param in_file `str()` with the file name.
       @param ignore_fields `list()` fields do be ignored on the read action.
       @param variant `str()` in regular expression to match with the design version of the BOM.
       @return `dict()` of the parts designed. The keys are the componentes references.
    '''

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
                        fields[name] = value # Do not create empty fields. This is useful
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
    logger.log(DEBUG_OVERVIEW, '# Getting from XML \'{}\' KiCad BoM...'.format(
                                    os.path.basename(in_file)) )
    file_h = open(in_file)
    root = BeautifulSoup(file_h, 'lxml')
    file_h.close()

    # Get the general information of the project BoM XML file.
    logger.log(DEBUG_OVERVIEW, 'Getting authorship data...')
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
    prj_info['date'] = title_find_all(root, 'date') or (datetime.strptime(time.ctime(os.path.getmtime(in_file)), '%a %b %d %H:%M:%S %Y').strftime("%Y-%m-%d %H:%M:%S") + ' (file)')

    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    logger.log(DEBUG_OVERVIEW, 'Getting parts library...')
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
    logger.log(DEBUG_OVERVIEW, 'Getting components...')
    components = {}
    for c in root.find('components').find_all('comp'):

        # Find the library used for this component.
        libsource = c.find('libsource')
        if libsource:
            # Create the key to look up the part in the libparts dict.
            #libpart = str(libsource['lib'] + SEPRTR + libsource['part'])
            libpart = str(libsource['lib']) + SEPRTR + str(libsource['part'])
        else:
            libpart = '???'
            logger.log(DEBUG_OVERVIEW, 'Fottprint library not assigned to {}'.format(''))#TODO

        # Initialize the fields from the global values in the libparts dict entry.
        # (These will get overwritten by any local values down below.)
        # (Use an empty dict if no part exists in the library.)
        fields = libparts.get(libpart, dict()).copy() # Make a copy! Don't use reference!
        try:
            del fields['refs'] # Delete this entry that was creating problem
                               # to group parts of differents sheets ISSUE #97.
        except KeyError:
            pass

        # Store the part key and its value.
        fields['libpart'] = libpart

        # Get the footprint for the part (if any) from the schematic.
        try:
            fields['value'] = str(c.find('value').string)
            fields['footprint'] = str(c.find('footprint').string)
            fields['datasheet'] = str(c.find('datasheet').string)
        except AttributeError:
            pass

        # Get the values for any other kicost-related fields in the part
        # (if any) from the schematic. These will override any field values
        # from the part library.
        fields.update(extract_fields(c, variant))

        # Store the fields for the part using the reference identifier as the key.
        components[str(c['ref'])] = fields

    return remove_dnp_parts(components, variant), prj_info
