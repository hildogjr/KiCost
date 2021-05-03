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
import time
from datetime import datetime
import re
from bs4 import BeautifulSoup
from collections import OrderedDict
from ..global_vars import logger, DEBUG_OVERVIEW, DEBUG_OBSESSIVE, SEPRTR
from .tools import field_name_translations
from .eda import eda_class


__all__ = ['eda_kicad']


def extract_fields(part, variant, ign_fields, distributors):
    # Extract XML fields from the part in a library or schematic.

    fields = {}
    try:
        for f in part.find('fields').find_all('field'):
            # Store the name and value for each kicost-related field.
            # Remove case of field name along with leading/trailing whitespace.
            name = str(f['name']).lower().strip()
            if name in ign_fields:
                continue  # Ignore fields in the ignore list.
            elif SEPRTR not in name:  # No separator, so get global field value.
                name = field_name_translations.get(name, name)
                value = str(f.string)
                if value and name not in fields:
                    # Only set the field if it is not set yet (which indicates a variant
                    # has been parsed before)
                    # Do not create empty fields. This is useful
                    # when used more than one `manf#` alias in one designator.
                    fields[name] = value
            else:
                name = str(f['name']).strip()
                name_ori = name
                # Now look for fields that start with 'kicost' and possibly
                # another dot-separated variant field and store their values.
                # Anything else is in a non-kicost namespace.
                key_re = r'kicost(\.(?P<variant>.*))?:(?P<name>.*)'
                mtch = re.match(key_re, name, flags=re.IGNORECASE)
                if mtch:
                    v = mtch.group('variant')
                    if v is not None:
                        if not re.match(variant, v, flags=re.IGNORECASE):
                            continue
                        logger.log(DEBUG_OBSESSIVE, 'Matched Variant ... ' + v + '.' + mtch.group('name'))
                    # The field name is anything that came after the leading
                    # 'kicost' and optional variant field.
                    name = mtch.group('name')
                    if SEPRTR in name:
                        # DISTRIBUTOR:FIELD
                        # Separate the distributor from the field name
                        idx = name.index(SEPRTR)
                        dist = name[:idx]
                        # Is this a supported distributor?
                        dist_l = dist.lower()
                        if dist_l in distributors:
                            # Use the lower case version
                            dist = dist_l
                        # Translate the field name
                        name = name[idx+1:].lower()
                        name = field_name_translations.get(name, name)
                        # Join both again
                        name = dist + SEPRTR + name
                    else:
                        # FIELD
                        # No distributor in the name
                        # Adapt it
                        name = name.lower()
                        name = field_name_translations.get(name, name)
                        # Is distributor related?
                        if name in ('cat#', 'pricing', 'link'):
                            # Add it to the default local distributor
                            logger.log(DEBUG_OBSESSIVE, 'Assigning name "{}" to "Local" distributor'.format(name))
                            name = 'Local:' + name
                        elif name in ('manf#', 'manf') or name[:-1] in distributors or v is not None:
                            # A part number
                            logger.log(DEBUG_OBSESSIVE, 'Moving name "{}" to "global" namespace'.format(name))
                        else:
                            # Not a part number, add it "local" namespace
                            logger.log(DEBUG_OBSESSIVE, 'Moving name "{}" to "local" namespace'.format(name))
                            name = 'local:' + name
                    value = str(f.string)
                    if value or v is not None:
                        # Empty value also propagated to force deleting default value
                        fields[name] = value
                    logger.log(DEBUG_OBSESSIVE, '{} Field {} -> {}={}'.format(str(part['ref']), name_ori, name, value))
    except AttributeError:
        pass  # No fields found for this part.
    return fields


def title_find_all(data, field):
    ''' Helper function for finding title info, especially if it is absent. '''
    try:
        return data.find_all(field)[0].string
    except (AttributeError, IndexError):
        return None


def get_part_groups(in_file, ignore_fields, variant, distributors):
    '''Get groups of identical parts from an XML file and return them as a dictionary.
       @param in_file `str()` with the file name.
       @param ignore_fields `list()` fields do be ignored on the read action.
       @param variant `str()` in regular expression to match with the design version of the BOM.
       @return `dict()` of the parts designed. The keys are the componentes references.
    '''
    distributors = set(distributors)

    ign_fields = [str(f.lower()) for f in ignore_fields]

    # Read-in the schematic XML file to get a tree and get its root.
    logger.log(DEBUG_OVERVIEW, '# Getting from XML \'{}\' KiCad BoM...'.format(
                                    os.path.basename(in_file)))
    file_h = open(in_file)
    root = BeautifulSoup(file_h, 'lxml')
    file_h.close()

    # Get the general information of the project BoM XML file.
    logger.log(DEBUG_OVERVIEW, 'Getting authorship data...')
    title = root.find('title_block')

    prj_info = dict()
    prj_info['title'] = title_find_all(title, 'title') or os.path.basename(in_file)
    prj_info['company'] = title_find_all(title, 'company')
    prj_info['date'] = title_find_all(root, 'date') or (datetime.strptime(time.ctime(os.path.getmtime(in_file)), '%a %b %d %H:%M:%S %Y')
                                                        .strftime("%Y-%m-%d %H:%M:%S") + ' (file)')

    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    logger.log(DEBUG_OVERVIEW, 'Getting parts library...')
    libparts = {}
    if root.find('libparts'):
        for p in root.find('libparts').find_all('libpart'):

            # Get the values for the fields in each library part (if any).
            fields = extract_fields(p, variant, ign_fields, distributors)

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
            logger.log(DEBUG_OVERVIEW, 'Footprint library not assigned to {}'.format(''))  # TODO

        # Initialize the fields from the global values in the libparts dict entry.
        # (These will get overwritten by any local values down below.)
        # (Use an empty dict if no part exists in the library.)
        fields = libparts.get(libpart, dict()).copy()  # Make a copy! Don't use reference!
        try:
            # Delete this entry that was creating problem
            # to group parts of differents sheets ISSUE #97.
            del fields['refs']
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
        fields.update(extract_fields(c, variant, ign_fields, distributors))

        # Store the fields for the part using the reference identifier as the key.
        components[str(c['ref'])] = fields

    return components, prj_info


class eda_kicad(eda_class):
    name = 'kicad'
    label = 'KiCad file'  # Label used on the GUI.
    desc = 'KiCad open source EDA.'

    @staticmethod
    def get_part_groups(in_file, ignore_fields, variant, distributors):
        return get_part_groups(in_file, ignore_fields, variant, distributors)

    @staticmethod
    def file_eda_match(content, extension):
        return extension == '.xml' and re.search(r'<tool\>Eeschema.*\<\/tool\>', content, re.IGNORECASE)


eda_class.register(eda_kicad)
