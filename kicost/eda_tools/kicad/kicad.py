# MIT license
#
# Copyright (C) 2015 by XESS Corporation
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

import re
from bs4 import BeautifulSoup
from ...kicost import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE
from ...kicost import SEPRTR
from ...kicost import field_name_translations
from ..eda_tools import subpart_split, groups_sort


# Temporary class for storing part group information.
class IdenticalComponents(object):
    pass


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
                name = str(f['name'].lower().strip())
                if name in ign_fields:
                    continue  # Ignore fields in the ignore list.
                elif SEPRTR not in name: # No separator, so get global field value.
                    name = field_name_translations.get(name, name)
                    fields[name] = str(f.string)
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
                        if name not in ('manf#', 'manf') and name[:-1] not in distributors:
                            if SEPRTR not in name: # This field has no distributor.
                                name = 'local:' + name # Assign it to a local distributor.
                        fields[name] = str(f.string)

        except AttributeError:
            pass  # No fields found for this part.
        return fields

    # Read-in the schematic XML file to get a tree and get its root.
    logger.log(DEBUG_OVERVIEW, 'Get schematic XML...')
    root = BeautifulSoup(in_file, 'lxml')

    # Get the general information of the project BoM XML file.
    title = root.find('title_block')
    prj_info = dict()
    prj_info['title'] = title.find_all('title')[0].string
    prj_info['company'] = title.find_all('company')[0].string
    prj_info['date'] = title.find_all('date')[0].string

    # Make a dictionary from the fields in the parts library so these field
    # values can be instantiated into the individual components in the schematic.
    logger.log(DEBUG_OVERVIEW, 'Get parts library...')
    libparts = {}
    for p in root.find('libparts').find_all('libpart'):

        # Get the values for the fields in each library part (if any).
        fields = extract_fields(p, variant)

        # Store the field dict under the key made from the
        # concatenation of the library and part names.
        libparts[str(p['lib'] + SEPRTR + p['part'])] = fields

        # Also have to store the fields under any part aliases.
        try:
            for alias in p.find('aliases').find_all('alias'):
                libparts[str(p['lib'] + SEPRTR + alias.string)] = fields
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
        libpart = str(libsource['lib'] + SEPRTR + libsource['part'])

        # Initialize the fields from the global values in the libparts dict entry.
        # (These will get overwritten by any local values down below.)
        fields = libparts[libpart].copy()  # Make a copy! Don't use reference!

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

    #print('Removed parts:', set(components.keys())-set(accepted_components.keys()))

    # Replace the component list with the list of accepted parts.
    components = subpart_split(accepted_components)

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

    # Sort the founded groups by BOM_ORDER definition.
    new_component_groups = groups_sort(new_component_groups)

    # Now return the list of identical part groups.
    return new_component_groups, prj_info
