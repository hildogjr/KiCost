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

# Libraries.
import re, os # Regular expression parser and matches.
from ..globals import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE # Debug configurations.
from ..globals import SEPRTR
from ..kicost import distributor_dict
from . import eda_tool_dict # EDA dictionary with the features.

__all__ = ['file_eda_match', 'partgroup_qty', 'groups_sort', 'order_refs', 'subpartqty_split', 'group_parts']

# Qty and part separators are escaped by preceding with '\' = (?<!\\)
QTY_SEPRTR  = r'(?<!\\)\s*[:]\s*'  # Separator for the subpart quantity and the part number, remove the lateral spaces.
PART_SEPRTR = r'(?<!\\)\s*[;,]\s*' # Separator for the part numbers in a list, remove the lateral spaces.
ESC_FIND = r'\\\s*([;,:])\s*'      # Used to remove backslash from escaped qty & manf# separators.
SUB_SEPRTR  = '#' # Subpart separator for a part reference.
REPLICATE_MANF = '~' # Character used to replicate the last manufacture name (`manf` field) in multiparts.
SGROUP_SEPRTR = '\n' # Separator of the semi identical parts groups (parts that have the filed ignored to group).
# Reference string order to the spreadsheet. Use this to
# group the elements in sequential rows.
BOM_ORDER = 'u,q,d,t,y,x,c,r,s,j,p,cnn,con'

# Characters removed from references when read the files.
PART_REF_REGEX_NOT_ALLOWED = '[\+\(\)\*\{}]'.format(SEPRTR)
# Regular expression for detecting part reference ids consisting of a
# prefix of letters followed by a sequence of digits, such as 'LED10'
# or a sequence of digits followed by a subpart number like 'CONN1#3'.
# There can even be an interposer alphabetical and some special
# characters so 'LED.10', 'LED_10', 'LED_BLUE-10', 'TEST&PIN+2',
# 'TEST+SUPPLY' or 'R4.10' is also OK.
# Also references with numbers at the end, just if the interlocutor,
# part are allowed by some EDAs or manual edition in KiCad.
# In the case of multiple project BOM files, the references are
# modified by adding the project number identification followed
# by `SEPRTR` definition.
PART_REF_REGEX_SPECIAL_CHAR_REF = '\+\-\=\s\_\.\(\)\$\*\&' # Used in next definition only (because repeat).
PART_REF_REGEX = re.compile('(?P<prefix>([a-z]*(?P<prj>\d+){p_sp})?(?P<ref>[a-z{sc}\d]*[a-z{sc}]))(?P<num>((?P<ref_num>\d+(\.\d+)?)({sp}(?P<subpart_num>\d+))?)?)'.format(p_sp=SEPRTR, sc=PART_REF_REGEX_SPECIAL_CHAR_REF, sp=SUB_SEPRTR), re.IGNORECASE)

# Generate a dictionary to translate all the different ways people might want
# to refer to part numbers, vendor numbers, manufacture name and such.
field_name_translations = {
    'mpn': 'manf#',
    'pn': 'manf#',
    'manf_num': 'manf#',
    'manf-num': 'manf#',
    'mfg_num': 'manf#',
    'mfg-num': 'manf#',
    'mfg#': 'manf#',
    'mfg part#': 'manf#',
    'man_num': 'manf#',
    'man-num': 'manf#',
    'man#': 'manf#',
    'mnf_num': 'manf#',
    'mnf-num': 'manf#',
    'mnf#': 'manf#',
    'mfr_num': 'manf#',
    'mfr-num': 'manf#',
    'mfr#': 'manf#',
    'part-num': 'manf#',
    'part_num': 'manf#',
    'p#': 'manf#',
    'part#': 'manf#',
    'manf': 'manf',
    'manufacturer': 'manf',
    'mnf': 'manf',
    'man': 'manf',
    'mfg': 'manf',
    'mfr': 'manf',
}
# Create the fields translate for each distributor submodule.
for stub in ['part#', '#', 'p#', 'pn', 'vendor#', 'vp#', 'vpn', 'num']:
    for dist in distributor_dict:
        field_name_translations[dist + stub] = dist + '#'
        field_name_translations[dist + '_' + stub] = dist + '#'
        field_name_translations[dist + '-' + stub] = dist + '#'

# Others fields used by KiCost and that have to be standardized.
field_name_translations.update(
    {
        'variant': 'variant',
        'version': 'variant',
        'dnp': 'dnp',
        'nopop': 'dnp',
        'description': 'desc',
        'pdf': 'datasheet',
    }
)


def file_eda_match(file_name):
    '''@brief Verify with which EDA the file matches.
       
       Return the EDA name with the file matches or `None` if not founded.
       @param file_name File `str` name.
       @return Name of the module corresponding to read the file or `None`to not recognized.
    '''
    try:
        file_handle = open(file_name, 'r')
        content = file_handle.read()
    except UnicodeDecodeError: # It happens with some Windows CSV files on Python 3.
        file_handle.close()
        file_handle = open(file_name, 'r', encoding ='ISO-8859-1')
        content = file_handle.read()
    extension = os.path.splitext(file_name)[1]
    for name, defs in eda_tool_dict.items():
        #print(name, extension==defs['file']['extension'], re.search(defs['file']['content'], content, re.IGNORECASE))
        if re.search(defs['file']['content'], content, re.IGNORECASE)\
            and extension==defs['file']['extension']:
                file_handle.close()
                return name
    file_handle.close()
    return None


def organize_parts(components, fields_merge):
    '''@brief Organize the parts to better do the scrape in the distributors.
       
       Remove the Not Populate Parts (DNP), split the components in unique
       parts, necessary because of some file formats that present the
       components already grouped and to finish, group them as group parts
       with same manufactures codes, company manufactures and distributors
       codes to not scrape repetitively the same part kind.
       
       @param  components Part components in a `list()` of `dict()`, format given by the EDA modules.
       @return `list()` of `dict()` with the component parts organized (grouped, removed the "not populate", ...)
    '''
    # Remove the Not Populate Parts.
    ##components = remove_dnp_parts(components, variant) # Do this inside each EDA submodule because of the ISSUE #73.
    # Split multi-components into individual subparts.
    components = subpartqty_split(components)
    # Group the components in group in the same characteristics (fields).
    components = group_parts(components, fields_merge)
    return components


# Temporary class for storing part group information.
class IdenticalComponents(object):
    '''@brief Class to group components.'''
    pass

def group_parts(components, fields_merge):
    '''@brief Group common parts after preprocessing from XML or CSV files.
       
       Group common parts looking in the existent files that could be merged
       by the use of `fields_merge`. First group all designed parts without
       look the manufacture/distributors codes, after see if any will be
       propagated (designed part with out information and same values,
       footprint and so on that other that have manufacture part, receive
       this code).
       Count the quantities of each part designed using the 'manf#_qty'
       field, this is important to merge subparts of different parts and
       parts of different BOMs (in the mode of multifiles).
       @param components Part components in a `list()` of `dict()`, format given by the EDA modules.
       @param fileds_merge Data fields of the `dict()` variable to be merged and ignored to make the identical components group (before be scraped in the distributors web site).
       @return `list()` of `dict()`
    '''

    logger.log(DEBUG_OVERVIEW, '# Grouping parts...')

    # All codes to scrape, do not include code field name of distributors
    # that will not be scraped. This definition is used to create and check
    # the identical groups or subsplit the seemingly identical parts.
    FIELDS_MANFCAT = ([d + '#' for d in distributor_dict] + ['manf#'])
    # Calculated all the fileds that never have to be used to create the hash keys.
    # These include all the manufacture company and codes, distributors codes 
    # recognized by the insalled modules and, quantity and sub quantity of the part.
    FIELDS_NOT_HASH = (['manf#_qty', 'manf'] + FIELDS_MANFCAT + [d + '#_qty' for d in distributor_dict])

    # Check if was asked to merge some not allowed fiels (as `manf`, `manf# ...
    # other ones as `desc` and even `value` and `footprint`may be merged due
    # the different typed (1uF and 1u) or footprint library names to the same one.
    fields_merge = list( [field_name_translations.get(f.lower(),f.lower()) for f in fields_merge] )
    for c in FIELDS_NOT_HASH:
        if c in fields_merge:
             raise ValueError('Manufacturer/distributor codes and manufacture company "{}" can\'t be ignored to create the components groups.'.format(c))
    FIELDS_NOT_HASH = FIELDS_NOT_HASH + fields_merge # Not use the fields do merge to create the hash.

    # Now partition the parts into groups of like components.
    # First, get groups of identical components but ignore any manufacturer's
    # part numbers that may be assigned. Just collect those in a list for each group.
    logger.log(DEBUG_OVERVIEW, 'Getting groups of identical components...')
    component_groups = {}
    for ref, fields in list(components.items()): # part references and field values.

        # Take the field keys and values of each part and create a hash.
        # Use the hash as the key to a dictionary that stores lists of
        # part references that have identical field values. The important fields
        # are the reference prefix ('R', 'C', etc.), value, and footprint.
        # Don't use the manufacturer's part number when calculating the hash!
        # Also, don't use any fields with SEPRTR in the label because that indicates
        # a field used by a specific tool (including KiCost).
        hash_fields = {k: fields[k] for k in fields if k not in FIELDS_NOT_HASH and SEPRTR not in k}
        h = hash(tuple(sorted(hash_fields.items())))

        # Now add the hashed component to the group with the matching hash
        # or create a new group if the hash hasn't been seen before.
        try:
            # Add next ref for identical part to the list.
            component_groups[h].refs.append(ref)
            # Also add any manufacturer's part number (or None) and each distributor
            # stock catologue code to the group's list.
            for f in FIELDS_MANFCAT:
                component_groups[h].manfcat_codes[f].add(fields.get(f))
        except KeyError:
            # This happens if it is the first part in a group, so the group
            # doesn't exist yet.
            component_groups[h] = IdenticalComponents()  # Add empty structure.
            component_groups[h].refs = [ref]  # Init list of refs with first ref.
            # Now add the manf. part code (or None) and each distributor stock
            # catologue code for this part to the group set.
            component_groups[h].manfcat_codes = {}
            for f in FIELDS_MANFCAT:
                component_groups[h].manfcat_codes[f] = set([fields.get(f)])
    #print('\n\n\n1++++++++++++++',len(component_groups))
    #for g,grp in list(component_groups.items()):
    #    print('\n', grp.refs)
    #    for r in grp.refs:
    #        print(r, components[r])


    # Now we have groups of seemingly identical parts. But some of the parts
    # within a group may have different manufacturer's part numbers, and these
    # groups may need to be split into smaller groups of parts all having the
    # same manufacturer's number. Here are the cases that need to be handled:
    #   One manf# number (and one cat# for each distributor):
    #       All parts have the same manf#. Don't split this group.
    #   Two manf# numbers (or cat# distributor code), but one is `None`:
    #       Some of the parts have no manf# or distributor# but are otherwise
    #       identical to the other parts in the group. Don't split this group.
    #       Instead, propagate the non-None manf# to all the parts.
    #   Two manf# (or two cat# distributor code), neither is `None`:
    #       All parts have non-`None` manf# and distributor# numbers. Split
    #       the group into two smaller groups of parts all having the same
    #       manf# and distributor#.
    #   Three or more manf# (or distributor#):
    #       Split this group into smaller groups, each one with parts having
    #       the same manf# and distributor#, even if it's `None`. It's
    #       impossible to determine which manf# the `None` parts should be
    #       assigned to, so leave their manf# as `None`.
    logger.log(DEBUG_OVERVIEW, 'Checking the seemingly identical parts group...')
    new_component_groups = [] # Copy new component groups into this.
    for g, grp in list(component_groups.items()):
        num_manfcat_codes = {f:len(grp.manfcat_codes[f]) for f in FIELDS_MANFCAT}
        if all([num_manfcat_codes[f]==1 or (num_manfcat_codes[f]==2 and None in grp.manfcat_codes[f]) for f in FIELDS_MANFCAT]):
            new_component_groups.append(grp)
            continue  # CASE ONE and TWO:
                      # Single manf# and distributor catalogue. Or a seemingly
                      # identical groupt with just one valid manf# or cat# code,
                      # the other one is `None`.Don't split this group. `None`
                      # will be replaced with the propagated manufacture /
                      # distributor catalogue code.
        elif all([(num_manfcat_codes[f]==1 and grp.manfcat_codes[f]==None) for f in FIELDS_MANFCAT]):
            new_component_groups.append(grp)
            continue  # CASE THREE:
                      # One manf# or cat# that is `None`. Don't split this
                      # group. These parts are not intended to be purchased.
        # CASE FOUR:
        # Otherwise, split the group into subgroups, each with the
        # same manf# and distributors catalogue codes (for that one
        # that will be scraped, the other ones are not considered).
        for i_manfcat in range(max([len(grp.manfcat_codes.get(f)) for f in FIELDS_MANFCAT])):
            manfcat_num = {}
            for f in FIELDS_MANFCAT:
                try:
                    manfcat_num[f] = list(grp.manfcat_codes.get(f))[i_manfcat]
                except IndexError:
                    # If not have more code in the set list, is because just
                    # exist one. So use this as general.
                    manfcat_num[f] = list(grp.manfcat_codes.get(f))[0]
            sub_group = IdenticalComponents()
            sub_group.manfcat_codes = [manfcat_num]
            sub_group.refs = []
            for ref in grp.refs:
                # Use get() which returns `None` if the component has no
                # manf# or distributor# field. That will match if the
                # group manf_num is also None. So append the par to the group.
                if all([components[ref].get(f)==manfcat_num[f] for f in FIELDS_MANFCAT]):
                    sub_group.refs.append(ref)
            new_component_groups.append(sub_group) # Append one part of the splited group.
    #print('\n\n\n2++++++++++++++',len(new_component_groups))
    #for grp in new_component_groups:
    #    print('\n', grp.refs)
    #    for r in grp.refs:
    #        print(r, components[r])

    # If the identical components grouped have difference in the `fields_merge`
    # so replace this field with a string composed line-by-line with the
    # ocorrences (definition `SGROUP_SEPRTR`) preceded with the refs
    # collapsed plus `SEPRTR`. Implementation of the ISSUE #102.
    logger.log(DEBUG_OVERVIEW, 'Merging field asked in the identical components groups...')
    if fields_merge:
        fields_merge = [field_name_translations.get(f.lower(), f.lower()) for f in fields_merge]
        for grp in new_component_groups:
            components_grp = dict()
            components_grp = {i:components[i] for i in grp.refs}
            for f in fields_merge:
                values_field = [v.get(f, '') for k,v in components_grp.items()]
                ocurrences = {v_g:[ r for r in grp.refs if components[r].get(f,'') == v_g] for v_g in set(values_field)}
                if len(ocurrences)>1:
                    if f=='desc' and len(ocurrences)==2 and '' in ocurrences.keys():
                        value = ''.join(list(ocurrences.keys()))
                    else:
                        value = SGROUP_SEPRTR.join( [','.join( order_refs(r) ) + SEPRTR + ' ' + t for t,r in ocurrences.items()] )
                    for r in grp.refs:
                        components[r][f] = value
    #print('\n\n\n3++++++++++++++',len(new_component_groups))
    #for grp in new_component_groups:
    #    print(grp.refs)
    #    for r in grp.refs:
    #        print(r, components[r])

    # Now get the values of all fields within the members of a group.
    # These will become the field values for ALL members of that group.
    logger.log(DEBUG_OVERVIEW, 'Propagating field values to identical components...')
    for grp in new_component_groups:
        grp_fields = {}
        qty = []
        for ref in grp.refs:
            for key, val in list(components[ref].items()):
                if key == 'manf#_qty':
                    try:
                        for i in range(len(val)):
                            grp_fields['manf#_qty'][i] += '+' + val[i] # DUMMY way and need improvement to really do arithmetic and not string cat. #TODO
                            val[i] = grp_fields['manf#_qty'][i] # Make the first values take also equal.
                    except:
                        grp_fields['manf#_qty'] = val
                    continue
                if val is None: # Field with no value...
                    continue # so ignore it.
                if grp_fields.get(key): # This field has been seen before.
                    if grp_fields[key] != val: # Flag if new field value not the same as old.
                        raise ValueError('Field value mismatch: ref={} field={} value=\'{}\', global=\'{}\' at group={}'.format(ref, key, val, grp_fields[key], grp.refs))
                else: # First time this field has been seen in the group, so store it.
                    grp_fields[key] = val
        grp.fields = grp_fields

    # Now return the list of identical part groups.
    #print('\n\n\n------------')
    #for grp in new_component_groups:
    #    print(grp.refs)
    #    for r in grp.refs:
    #        print(r, components[r])
    return new_component_groups


def remove_dnp_parts(components, variant):
    '''@brief Remove the DNP parts or not assigned to the current variant.
       
       Remove components that are assigned to a variant that is not the current variant,
       or which are "do not populate" (DNP). (Any component that does not have a variant
       is assigned the current variant so it will not be removed unless it is also DNP.)
       
       @param components Part components in a `list()` of `dict()`, format given by the EDA modules.
       @return `list()` of `dict()`.
    '''

    logger.log(DEBUG_OVERVIEW, '# Removing do not populate parts...')

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
    
    return accepted_components


def groups_sort(new_component_groups):
    '''@brief Order the groups in a alphabetical way.
       
       Put the components groups in the spreadsheet rows in a specific order
       using the reference string of the components. The order is defined
       by BOM_ORDER.
       @param components Part components in a `list()` of `dict()`, format given by the EDA modules.
       @return Same as input.
    '''

    logger.log(DEBUG_OVERVIEW, 'Sorting the groups for better visualization...')

    ref_identifiers = re.split('(?<![\W\*\/])\s*,\s*|\s*,\s*(?![\W\*\/])',
                BOM_ORDER, flags=re.IGNORECASE)
    component_groups_order_old = list( range(0,len(new_component_groups)) )
    component_groups_order_new = list()
    component_groups_refs = [new_component_groups[g].fields.get('reference') for g in component_groups_order_old]
    logger.log(DEBUG_OBSESSIVE, 'All ref identifier: {}'.format(ref_identifiers) )
    logger.log(DEBUG_OBSESSIVE, '{} groups of components.'.format(len(component_groups_order_old)) )
    logger.log(DEBUG_OBSESSIVE, 'Identifiers founded {}.'.format(component_groups_refs) )
    for ref_identifier in ref_identifiers:
        component_groups_ref_match = [i for i in range(0,len(component_groups_refs)) if ref_identifier==component_groups_refs[i].lower()]
        logger.log(DEBUG_OBSESSIVE, 'Identifier: {} in {}.'.format(ref_identifier, component_groups_ref_match) )
        if len(component_groups_ref_match)>0:
            # If found more than one group with the reference, use the 'manf#'
            # as second order criteria.
            if len(component_groups_ref_match)>1:
                try:
                    for item in component_groups_ref_match:
                        component_groups_order_old.remove(item)
                except ValueError:
                    pass
                # Examine 'manf#' and refs to get the order.
                # Order by refs that have 'manf#' codes, that ones that don't have stay at the end of the group.
                group_manf_list = [new_component_groups[h].fields.get('manf#') for h in component_groups_ref_match]
                group_refs_list = [new_component_groups[h].refs for h in component_groups_ref_match]
                sorted_groups = sorted(range(len(group_refs_list)), key=lambda k:(group_manf_list[k] is None,  group_refs_list[k]))
                logger.log(DEBUG_OBSESSIVE, '{} > order: {}'.format( group_manf_list, sorted_groups) )
                component_groups_ref_match = [component_groups_ref_match[i] for i in sorted_groups]
                component_groups_order_new += component_groups_ref_match
            else:
                try:
                    component_groups_order_old.remove(component_groups_ref_match[0])
                except ValueError:
                    pass
                component_groups_order_new += component_groups_ref_match
    # The new order is the found refs firt and at the last the not referenced in BOM_ORDER.
    component_groups_order_new += component_groups_order_old # Add the missing references groups.
    new_component_groups = [new_component_groups[i] for i in component_groups_order_new]
    return new_component_groups


def subpartqty_split(components):
    '''@brief Split the components with subparts in different components.
       
       Take each part and the all manufacture/distributors combination
       possibility to split in subpart the components part that have
       more than one manufacture/distributors code.
       For each designator...
       For designator with a "single subpart" check with the quantity
       is more than one.
       
       @param components Part components in a `list()` of `dict()`, format given by the EDA modules.
       @return Same as the input.
    '''
    logger.log(DEBUG_OVERVIEW, 'Splitting subparts in the manufacture / distributors codes...')

    FIELDS_MANF = [d+'#' for d in distributor_dict]
    FIELDS_MANF.append('manf#')

    splitted_components = {}
    for part_ref, part in components.items():
        try:
            # Divide the subparts in different parts keeping the other fields
            # (reference, description, ...).
            # First search for the used filed to manufacture/distributor numbers
            # and how many subparts are in them. Use the loop also to extract the
            # manufacture/distributor codes in list.
            founded_fields = []
            subparts_qty = 0
            subparts_manf_code = dict()
            for field_code in FIELDS_MANF:
                if field_code in part:
                    subparts_qty = max(subparts_qty, 
                            len( subpart_list(part[field_code]) ) ) # Quantity of sub parts.
                    founded_fields += [field_code]
                    subparts_manf_code[field_code] = subpart_list(part[field_code])
            if not founded_fields:
                splitted_components[part_ref] = part
                continue # If not manf/distributor code pass to next.
            # Divide the `manf` manufacture name.
            try:
                subparts_manf = subpart_list(part['manf'])
                if len(subparts_manf)!=subparts_qty:
                    if len(subparts_manf)==1:
                        # If just one `manf`assumes that is for all.
                        subparts_manf = [subparts_manf[0]]*subparts_qty
                    else:
                        # Exception `manf` and `manf#` length doesn't macth, fill with '' at the end.
                        subparts_manf.extend(['']*(subparts_qty-len(subparts_manf)))
            except KeyError:
                subparts_manf = ['']*subparts_qty
                pass

            logger.log(DEBUG_DETAILED, '{} >> {}'.format(part_ref, founded_fields) )

            # Second, if more than one subpart, split the sub parts as
            # new components with the same description, footprint, and
            # so on... Get the subpart.
            if subparts_qty>1:
                # Remove the actual part from the list.
                part_actual = part
                part_actual_value = part_actual['value']
                subpart_part = ''
                subpart_qty = ''
                # Add the splited subparts.
                for subparts_index in range(subparts_qty):
                    # Create a sub component based on the main component with
                    # the subparts. Modify the designator and the part. Create
                    # a sub quantity field.
                    subpart_actual = part_actual.copy()
                    for field_manf_dist_code in founded_fields:
                        # For each manufacture/distributor code take the same order of
                        # the code list and split in each subpart. When not founded one
                        # part, do not add.
                        # e.g. U1:{'manf#':'PARTG1;PARTG2;PARTG3', 'mouser#''PARTM1;PARTM2'}
                        # result:
                        # U1.1:{'manf#':'PARTG1', 'mouser#':'PARTM1'}
                        # U1.2:{'manf#':'PARTG2', 'mouser#':'PARTM2'}
                        # U1.3:{'manf#':'PARTG3'}
                        try:
                            p_manf_code = subparts_manf_code[field_manf_dist_code][subparts_index]
                            subpart_actual['value'] = '{v} - p{idx}/{total}'.format(
                                            v=part_actual_value,
                                            idx=subparts_index+1,
                                            total=subparts_qty)
                            subpart_qty, subpart_part = manf_code_qtypart(p_manf_code)
                            subpart_actual[field_manf_dist_code] = subpart_part
                            subpart_actual[field_manf_dist_code+'_qty'] = subpart_qty
                            logger.log(DEBUG_OBSESSIVE, subpart_actual)
                        except IndexError:
                            pass
                    # Update the splitted `manf`(manufactures names).
                    if subparts_manf[subparts_index]!=REPLICATE_MANF:
                        # If the actual manufacture name is the defined as `REPLICATE_MANF`
                        # replicate the last one.
                        p_manf = subparts_manf[subparts_index]
                    subpart_actual['manf'] = p_manf
                    # Update the description and reference of the part.
                    ref = part_ref + SUB_SEPRTR + str(subparts_index + 1)
                    splitted_components[ref] = subpart_actual
            else:
                part_actual = part.copy()
                for field_manf_dist_code in founded_fields:
                    # When one "single subpart" also use the logic of quantity.
                    try:
                        p_manf_code = subparts_manf_code[field_manf_dist_code][0]
                        part_qty, part_part = manf_code_qtypart(p_manf_code)
                        part_actual[field_manf_dist_code] = part_part
                        part_actual[field_manf_dist_code+'_qty'] = part_qty
                        logger.log(DEBUG_OBSESSIVE, part)
                        splitted_components[part_ref] = part_actual
                    except IndexError:
                        pass
        except KeyError:
            continue

    return splitted_components


def partgroup_qty(component):
    '''@brief Take the components grouped quantity.
       
       Calculate the string of the quantity of the group parsing the
       reference (design) quantity and the sub quantity (in case that
       was a sub part of a manufacture/distributor code).
       In the case of the multifiles BOM (and future revision of the
       code) just use the 'manf#_qty' field that in `group_parts()`
       recorded the quantities used in each project.
       
       @param components Part component `dict()`, format given by the EDA modules.
       @return Quantity of the manf# part used.
    '''
    try:
        qty = component.fields.get('manf#_qty')

        logger.log(DEBUG_OBSESSIVE, 'Qty>> {}\t {}*{}'.format(component.refs, qty, component.fields.get('manf#')) )

        if isinstance(qty, list):
            # Multifiles BOM case, the quantities in the list represent
            # each project read by the order. Do not `CEILING` because
            # this is will be made in the total columns that sum all
            # the quantities needed in all projects BOMs.
            string = ['={{}}*({qp})'.format(qp=i) for i in qty]
        else:
            if qty != '1' and qty != None:
                string = '=CEILING({{}}*({q})*{qty},1)'.format(
                                q=qty,
                                qty=len(component.refs))
            else:
                string = '={{}}*{qty}'.format(qty=len(component.refs))
    except (KeyError, TypeError):
        logger.log(DEBUG_OBSESSIVE, 'Qty>> {} \t {}'.format(component.refs, len(component.refs)) )
        string = '={{}}*{qty}'.format(qty=len(component.refs))
    return string


def subpart_list(part):
    '''
    @brief Split the subpart by the `PART_SEPRTR`definition.
    
    Get the list of sub parts manufacture / distributor code
    numbers stripping the spaces and keeping the sub part
    quantity information, these have to be separated by
    PART_SEPRTR definition.
    
    @param part Manufacture code part `str`.
    @return List of manufacture code parts.
    '''
    return re.split(PART_SEPRTR, part.strip())


def manf_code_qtypart(subpart):
    '''@brief Get the quantity and the part code of the sub part
       manufacture / distributor. Test if was pre or post
       multiplied by a constant.
       
       Setting QTY_SEPRTR as '\:', we have
       ' 4.5 : ADUM3150BRSZ-RL7' -> ('4.5', 'ADUM3150BRSZ-RL7')
       '4/5  : ADUM3150BRSZ-RL7' -> ('4/5', 'ADUM3150BRSZ-RL7')
       '7:ADUM3150BRSZ-RL7' -> ('7', 'ADUM3150BRSZ-RL7')
       'ADUM3150BRSZ-RL7 :   7' -> ('7', 'ADUM3150BRSZ-RL7')
       'ADUM3150BRSZ-RL7' -> ('1', 'ADUM3150BRSZ-RL7')
       'ADUM3150BRSZ-RL7:' -> ('1', 'ADUM3150BRSZ-RL7') forgot the qty understood '1'
       
       @param Part that way have different than ONE quantity. Intended as one element of the list of `subpart_list()`.
       @return (qty, manf#) Quantity and the manufacture code.
    '''
    subpart = re.sub(ESC_FIND, r'\1', subpart) # Remove any escape backslashes preceding PART_SEPRTR.
    strings = re.split(QTY_SEPRTR, subpart)
    if len(strings)==2:
        # Search for numbers, matching with simple, frac and decimal ones.
        num_format = re.compile("^\s*[\-\+]?\s*[0-9]*\s*[\.\/]*\s*?[0-9]*\s*$")
        string0_test = re.match(num_format, strings[0])
        string1_test = re.match(num_format, strings[1])
        if string0_test and not(string1_test):
            qty = strings[0].strip()
            part = strings[1].strip()
        elif not(string0_test) and string1_test:
            qty = strings[1].strip()
            part = strings[0].strip()
        elif string0_test and string1_test:
            # May be founded a just numeric manufacture/distributor part,
            # in this case, the quantity is a shortest string not
            #considering "." and "/" marks.
            if len(re.sub('[\.\/]','',strings[0])) < len(re.sub('[\.\/]','',strings[1])):
                qty = strings[0].strip()
                part = strings[1].strip()
            else:
                qty = strings[1].strip()
                part = strings[0].strip()
        else:
            qty = '1'
            part = strings[0].strip() + strings[1].strip()
        if qty=='':
            qty = '1'
    else:
        qty = '1'
        part = ''.join(strings)
    logger.log(DEBUG_OBSESSIVE, 'part/qty>> {}\t\tpart>>{}\tqty>>'.format(subpart, part, qty) )
    return qty, part


def order_refs(refs, collapse=True):
    '''@brief Collapse list of part references into a sorted, comma-separated list of hyphenated ranges. This is intended as opposite of `split_refs()`
       @param refs Designator/references `list()`.
       @return References in a organized view way.
    '''

    def convert_to_ranges(nums):
        # Collapse a list of numbers into sorted, comma-separated, hyphenated ranges.
        # e.g.: 3,4,7,8,9,10,11,13,14 => 3,4,7-11,13,14

        def get_refnum(refnum):
            return int(re.match('\d+', refnum).group(0))

        def to_int(n):
            try:
                return int(n)
            except ValueError:
                return n

        nums.sort(key=get_refnum)  # Sort all the numbers.
        nums = [to_int(n) for n in nums]  # Convert strings to `int` if possible.
        num_ranges = []  # No ranges found yet since we just started.
        range_start = 0  # First possible range is at the start of the list of numbers.

        # Go through the list of numbers looking for 3 or more sequential numbers.
        while range_start < len(nums):
            num_range = nums[range_start]  # Current range starts off as a single number.
            next_range_start = range_start + 1  # The next possible start of a range.
            # Part references with subparts are never included in ref ranges.
            if not isinstance(num_range, int):
                num_ranges.append(num_range)
                range_start = next_range_start
                continue
            # Look for sequences of three or more sequential numbers.
            for range_end in range(range_start + 2, len(nums)):
                if not isinstance(nums[range_end], int):
                    break  # Ref with subpart, so can't be in a ref range.
                if range_end - range_start != nums[range_end] - nums[range_start]:
                    break  # Non-sequential numbers found, so break out of loop.
                # Otherwise, extend the current range.
                num_range = [nums[range_start], nums[range_end]]
                # 3 or more sequential numbers found, so next possible range must start after this one.
                next_range_start = range_end + 1
            # Append the range (or single number) just found to the list of range.
            num_ranges.append(num_range)
            # Point to the start of the next possible range and keep looking.
            range_start = next_range_start

        return num_ranges

    prefix_nums = {}  # Contains a list of numbers for each distinct prefix.
    for ref in refs:
        # Partition each part reference into its beginning part prefix and ending number.
        match = re.search(PART_REF_REGEX, ref)
        if match:
            prefix = match.group('prefix')
            num = match.group('num')
        else:
            # The not `match` happens when the user schematic designer use
            # not recognized characters by the `PART_REF_REGEX` definition
            # into the components references.
            raise ValueError('Not recognized characters used in <' + ref + '> reference. Advise: edit it in your BOM/Schematic.')

        # Append the number to the list of numbers for this prefix, or create a list
        # with a single number if this is the first time a particular prefix was encountered.
        prefix_nums.setdefault(prefix, []).append(num)

    # Convert the list of numbers for each ref prefix into ranges.
    if collapse:
        for prefix in list(prefix_nums.keys()):
            prefix_nums[prefix] = convert_to_ranges(prefix_nums[prefix])
    else:
        for prefix in list(prefix_nums.keys()):
            def get_refnum(refnum):
                return int(re.match('\d+', refnum).group(0))
            prefix_nums[prefix].sort(key=get_refnum)

    # Combine the prefixes and number ranges back into part references.
    collapsed_refs = []
    for prefix, nums in list(prefix_nums.items()):
        for num in nums:
            if isinstance(num, list):
                # Convert a range list into a collapsed part reference:
                # e.g., 'R10-R15' from 'R':[10,15].
                collapsed_refs.append('{0}{1}-{0}{2}'.format(prefix, num[0], num[-1]))
            else:
                # Convert a single number into a simple part reference: e.g., 'R10'.
                collapsed_refs.append('{}{}'.format(prefix, num))

    return collapsed_refs # Return the collapsed par references.


def split_refs(text):
    '''@brief Split string grouped references into a unique designator. This is intended as opposite of `order_refs(?, collapse=True)`
       
       'C17/18/19/20' --> ['C17','C18','C19','C20']
       'C17\18\19\20' --> ['C17','C18','C19','C20']
       'D33-D36' --> ['D33','D34','D35','D36']
       'D33-36' --> ['D33','D34','D35','D36']
       Also ignore some characters as '.' or ':' used in some cases of references.
       
       @param text Designator/references worn by a group of parts.
       @return Designator/references `list()` splitted.
    '''
    partial_ref = re.split(' *[,; ] *', text) # Split ignoring the spaces.
    refs = []
    for ref in partial_ref:
        # Remove invalid characters. Changed `PART_REF_REGEX_SPECIAL_CHAR_REF` definition and allowed special characters.
        #ref = re.sub('\+$', 'p', ref) # Finishing "+".
        ref = re.sub(PART_REF_REGEX_NOT_ALLOWED, '', ref) # Generic special characters not allowed. To work around #ISSUE #89.
        #ref = re.sub('\-+', '-', ref) # Double "-".
        #ref = re.sub('^\-', '', ref) # Starting "-".
        #ref = re.sub('\-$', 'n', ref) # Finishing "-".
        if re.search('^\w+\d', ref):
            if re.search('-', ref):
                designator_name = re.findall('^\D+', ref)[0]
                splitted_nums = re.split('-', ref)
                designator_name += ''.join( re.findall('^d*\W', splitted_nums[0] ) )
                splitted_nums = [re.sub(designator_name,'',splitted_nums[i]) for i in range(len(splitted_nums))]
                
                # Some EDAs may use some separator in the reference numeric parts, as
                # Altium that use "." (or even other) e.g. "R2.1,R2.2" to the same "R2"
                # replicated between schematics / rooms.
                base_splitted_nums = ''.join( re.findall('^\d+\D', splitted_nums[0]) )
                splitted_nums = [''.join( re.findall('\D*(\d+)$', n) ) for n in splitted_nums]
                
                splitted = list( range( int(splitted_nums[0]), int(splitted_nums[1])+1 ) )
                #splitted = [designator_name+str(splitted[i]) for i in range(len(splitted)) ]
                splitted = [designator_name +base_splitted_nums+str(splitted[i]) for i in range(len(splitted)) ]
                
                refs += splitted
            elif re.search('[/\\\]', ref):
                designator_name = re.findall('^\D+',ref)[0]
                splitted_nums = [re.sub('^'+designator_name, '', i) for i in re.split('[/\\\]',ref)]
                refs += [designator_name+i for i in splitted_nums]
            else:
                refs += [ref.strip()]
        else:
            # The designator name is not for a group of components and 
            # "\", "/" or "-" is part of the name. This characters have
            # to be removed.
            ref = re.sub('[\-\/\\\]', '', ref.strip())
            if not re.search(PART_REF_REGEX, ref).group('num'):
                # Add a '0' number at the end to be compatible with KiCad/KiCost
                # ref strings. This may be missing in the hand made BoM.
                ref += '0'
            refs += [ref]
    return refs
