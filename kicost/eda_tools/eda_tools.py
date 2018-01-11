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
from sys import exit # Exit in the error.
from ..kicost import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE # Debug configurations.
from ..distributors import distributors # Distributors name to use as field.
from ..kicost import distributors, SEPRTR
from . import eda_tool # EDA dictionary with the features.

__all__ = ['file_eda_match', 'subpart_qty', 'groups_sort', 'collapse_refs', 'group_parts']

# Qty and part separators are escaped by preceding with '\' = (?<!\\)
QTY_SEPRTR  = r'(?<!\\)\s*[:]\s*'  # Separator for the subpart quantity and the part number, remove the lateral spaces.
PART_SEPRTR = r'(?<!\\)\s*[;,]\s*' # Separator for the part numbers in a list, remove the lateral spaces.
ESC_FIND = r'\\\s*([;,:])\s*'      # Used to remove backslash from escaped qty & manf# separators.
SUB_SEPRTR  = '#' # Subpart separator for a part reference.
REPLICATE_MANF = '~' # Character used to replicate the last manufacture name (`manf` field) in multiparts.
# Reference string order to the spreadsheet. Use this to
# group the elements in sequencial rows.
BOM_ORDER = 'u,q,d,t,y,x,c,r,s,j,p,cnn,con'

# Regular expression for detecting part reference ids consisting of a
# prefix of letters followed by a sequence of digits, such as 'LED10'
# or a sequence of digits followed by a subpart number like 'CONN1#3'.
# There can even be an interposer character so 'LED.10', 'LED_10',
# 'LED_BLUE-10', 'TEST&PIN+2' or 'TEST+SUPPLY' is also OK.
# References with numbers at the end are allowed by some EDAs.
PART_REF_REGEX_NOT_ALLOWED = '[\+\.\(\)\*]'
PART_REF_REGEX_SPECIAL_CHAR_REF = '\+\-\=\s\_\.\(\)\$\*\&'
PART_REF_REGEX = re.compile('(?P<prefix>[a-z{sc}\d]*[a-z{sc}])(?P<num>((?P<ref_num>\d+)({sp}(?P<subpart_num>\d+))?)?)'.format(sc=PART_REF_REGEX_SPECIAL_CHAR_REF, sp=SUB_SEPRTR), re.IGNORECASE)

# Generate a dictionary to translate all the different ways people might want
# to refer to part numbers, vendor numbers, and such.
field_name_translations = {
    'mpn': 'manf#',
    'pn': 'manf#',
    'manf_num': 'manf#',
    'manf-num': 'manf#',
    'mfg_num': 'manf#',
    'mfg-num': 'manf#',
    'mfg#': 'manf#',
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
}
for stub in ['part#', '#', 'p#', 'pn', 'vendor#', 'vp#', 'vpn', 'num']:
    for dist in distributors:
        field_name_translations[dist + stub] = dist + '#'
        field_name_translations[dist + '_' + stub] = dist + '#'
        field_name_translations[dist + '-' + stub] = dist + '#'
field_name_translations.update(
    {
        'manf': 'manf',
        'manufacturer': 'manf',
        'mnf': 'manf',
        'man': 'manf',
        'mfg': 'manf',
        'mfr': 'manf',
    }
)
field_name_translations.update(
    {
        'variant': 'variant',
        'version': 'variant',
    }
)
field_name_translations.update(
    {
        'dnp': 'dnp',
        'nopop': 'dnp',
    }
)


def file_eda_match(file_name):
    '''Verify with which EDA the file matches.'''
    # Return the EDA name with the file matches or `None` if not founded.
    file_handle = open(file_name, 'r')
    content = file_handle.read()
    extension = os.path.splitext(file_name)[1]
    for name, defs in eda_tool.items():
        #print(name, extension==defs['file']['extension'], re.search(defs['file']['content'], content, re.IGNORECASE))
        if re.search(defs['file']['content'], content, re.IGNORECASE)\
            and extension==defs['file']['extension']:
                file_handle.close()
                return name
    file_handle.close()
    return None



# Temporary class for storing part group information.
class IdenticalComponents(object):
    pass

def group_parts(components):
    '''Group common parts after preprocessing from XML or CSV files.'''
    
    # Split multi-components into individual subparts.
    components = subpart_split(components)

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

    # Now return the list of identical part groups.
    return new_component_groups


def groups_sort(new_component_groups):
    '''
    Put the components groups in the spreadsheet rows in a spefic order
    using the reference string of the components. The order is defined
    by BOM_ORDER.
    '''
    ref_identifiers = re.split('(?<![\W\*\/])\s*,\s*|\s*,\s*(?![\W\*\/])',
                BOM_ORDER, flags=re.IGNORECASE)
    component_groups_order_old = list( range(0,len(new_component_groups)) )
    component_groups_order_new = list()
    component_groups_refs = [new_component_groups[g].fields.get('reference') for g in component_groups_order_old]
    if logger.isEnabledFor(DEBUG_OBSESSIVE):
        print('All ref identifier: ', ref_identifiers)
        print(len(component_groups_order_old), 'groups of components')
        print('Identifiers founded', component_groups_refs)
    for ref_identifier in ref_identifiers:
        component_groups_ref_match = [i for i in range(0,len(component_groups_refs)) if ref_identifier==component_groups_refs[i].lower()]
        if logger.isEnabledFor(DEBUG_OBSESSIVE):
            print('Identifier: ', ref_identifier, ' in ', component_groups_ref_match)
        if len(component_groups_ref_match)>0:
            # If found more than one group with the reference, use the 'manf#'
            # as second order criterian.
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
                if logger.isEnabledFor(DEBUG_OBSESSIVE):
                    print(group_manf_list,' > order: ', sorted_groups)
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


def subpart_split(components):
    '''
    Take each part and the all manufacture/distributors combination
    possibility to split in subpart the components part that have
    more than one manufacture/distributors code.
    For each designator...
    For designator with a "single subpart" check with the quantity
    is more than one.
    '''
    logger.log(DEBUG_OVERVIEW, 'Search for subparts within parts...')

    dist = [d+'#' for d in distributors]
    dist.append('manf#')

    splitted_components = {}
    for part_ref, part in components.items():
        try:
            # Divide the subparts in diferent parts keeping the other fields
            # (reference, description, ...).
            # First search for the used filed to manufacture/distributor numbers
            # and how many subparts are in them. Use the loop also to extract the
            # manufacture/distributor codes in list.
            founded_fields = []
            subparts_qty = 0
            subparts_manf_code = dict()
            for field_code in dist:
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

            if logger.isEnabledFor(DEBUG_DETAILED):
                print(part_ref, '>>', founded_fields)

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
                            if logger.isEnabledFor(DEBUG_OBSESSIVE):
                                print(subpart_actual)
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
                        if logger.isEnabledFor(DEBUG_OBSESSIVE):
                            print(part)
                        splitted_components[part_ref] = part_actual
                    except IndexError:
                        pass
        except KeyError:
            continue

    return splitted_components


def subpart_qty(component):
    '''
    Calculate the string of the quantity of the item parsing the
    referente (design) quantity and the sub quantity (in case that
    was a sub part of a manufacture/distributor code).
    '''
    try:
        subqty = component.fields.get('manf#_qty')

        if logger.isEnabledFor(DEBUG_OBSESSIVE):
            print('Qty>>',component.refs,'>>', subqty, '*',
                    component.fields.get('manf#'))

        if subqty != '1' and subqty != None:
            string = '=CEILING({{}}*({subqty})*{qty},1)'.format(
                            subqty=subqty,
                            qty=len(component.refs))
        else:
            string = '={{}}*{qty}'.format(qty=len(component.refs))
    except (KeyError, TypeError):
        if logger.isEnabledFor(DEBUG_OBSESSIVE):
            print('Qty>>',component.refs,'>>',len(component.refs))
        string = '={{}}*{qty}'.format(qty=len(component.refs))
    return string


def subpart_list(part):
    '''
    Get the list of sub parts manufacture / distributor code
    numbers stripping the spaces and keeping the sub part
    quantity information, these have to be separated by
    PART_SEPRTR definition.
    '''
    return re.split(PART_SEPRTR, part.strip())


def manf_code_qtypart(subpart):
    '''
    Get the quantity and the part code of the sub part
    manufacture / distributor. Test if was pre or post
    multiplied by a constant.
    Setting QTY_SEPRTR as '\:', we have
    ' 4.5 : ADUM3150BRSZ-RL7' -> ('4.5', 'ADUM3150BRSZ-RL7')
    '4/5  : ADUM3150BRSZ-RL7' -> ('4/5', 'ADUM3150BRSZ-RL7')
    '7:ADUM3150BRSZ-RL7' -> ('7', 'ADUM3150BRSZ-RL7')
    'ADUM3150BRSZ-RL7 :   7' -> ('7', 'ADUM3150BRSZ-RL7')
    'ADUM3150BRSZ-RL7' -> ('1', 'ADUM3150BRSZ-RL7')
    'ADUM3150BRSZ-RL7:' -> ('1', 'ADUM3150BRSZ-RL7') forgot the qty understood '1'
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
    if logger.isEnabledFor(DEBUG_OBSESSIVE):
        print('part/qty>>', subpart, '\t\tpart>>', part, '\tqty>>', qty)
    return qty, part


def collapse_refs(refs):
    '''Collapse list of part references into a sorted, comma-separated list of hyphenated ranges.'''

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
        nums = [to_int(n) for n in nums]  # Convert strings to ints if possible.
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
            # The not `match` happens when the user schematic disegner use
            # not recognized characters by the `PART_REF_REGEX` definition
            # into the components references.
            exit('Not recognized characters used in <' + ref + '> reference. Adivise: edit it in your BOM/Schematic.')

        # Append the number to the list of numbers for this prefix, or create a list
        # with a single number if this is the first time a particular prefix was encountered.
        prefix_nums.setdefault(prefix, []).append(num)

    # Convert the list of numbers for each ref prefix into ranges.
    for prefix in list(prefix_nums.keys()):
        prefix_nums[prefix] = convert_to_ranges(prefix_nums[prefix])

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

    # Return the collapsed par references.
    return ','.join(collapsed_refs)


def split_refs(text):
    '''Split string grouped references into a unique designator.'''
    # 'C17/18/19/20' --> ['C17','C18','C19','C20']
    # 'C17\18\19\20' --> ['C17','C18','C19','C20']
    # 'D33-D36' --> ['D33','D34','D35','D36']
    # 'D33-36' --> ['D33','D34','D35','D36']
    # Also ignore some caracheters as '.' or ':' used in some cases of references.
    partial_ref = re.split('[,;]', text)
    refs = []
    for ref in partial_ref:
        # Remove invalid characters. Changed `PART_REF_REGEX_SPECIAL_CHAR_REF` definiton and allowed special characters.
        #ref = re.sub('\+$', 'p', ref) # Finishing "+".
        ref = re.sub(PART_REF_REGEX_NOT_ALLOWED, '', ref) # Generic special caracheters not allowed. To work around #ISSUE #89.
        #ref = re.sub('\-+', '-', ref) # Double "-".
        #ref = re.sub('^\-', '', ref) # Starting "-".
        #ref = re.sub('\-$', 'n', ref) # Finishing "-".
        if re.search('^\w+\d', ref):
            if re.search('-', ref):
                designator_name = re.findall('^\D+', ref)[0]
                splitted_nums = re.split('-', ref)
                designator_name += ''.join( re.findall('^d*\W', splitted_nums[0] ) )
                splitted_nums = [re.sub(designator_name,'',splitted_nums[i]) for i in range(len(splitted_nums))]
                splitted = list( range( int(splitted_nums[0]), int(splitted_nums[1])+1 ) )
                splitted = [designator_name+str(splitted[i]) for i in range(len(splitted)) ]
                refs += splitted
            elif re.search('[/\\\]', ref):
                designator_name = re.findall('^\D+',ref)[0]
                splitted_nums = [re.sub('^'+designator_name, '', i) for i in re.split('[/\\\]',ref)]
                refs += [designator_name+i for i in splitted_nums]
            else:
                refs += [ref]
        else:
            # The designator name is not for a group of components and 
            # "\", "/" or "-" is part of the name. This characters have
            # to be removed.
            ref = re.sub('[\-\/\\\]', '', ref)
            if not re.search(PART_REF_REGEX, ref).group('num'):
                # Add a '0' number at the end to be compatible with KiCad/KiCost
                # ref strings. This may be missing in the hand made BoM.
                ref += '0'
            refs += [ref]
    return refs
