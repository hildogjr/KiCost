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

# Libraries.
import re # Regular expression parser.
from ..kicost import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE
from ..distributors import distributors # Distributors name to use as field.

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

__all__ = ['subpart_split','subpart_qty']

QTY_SEPRTR = '[\:]' # Separator for the subpart quantity and the part number.
PART_SEPRTR = '[\;\,]' # Separator for the part numbers in a list.
SUB_SEPRTR = '#' # Subpart separator for a part reference.

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


# ------------------ Public functions

# Functions to parse the manufacturer / distributor code to allow parts
# composed of subparts with different part codes.


def subpart_split(components):
    '''
    Take each part and the all manufacture/distributors combination
    possibility to split in subpart the components part that have
    more than one manufacture/distributors code.
    For each designator...
    '''
    logger.log(DEBUG_OVERVIEW, 'Search for subparts within parts...')

    dist = [d+'#' for d in distributors]
    dist.append('manf#')

    split_components = {}
    for part_ref, part in components.items():
        try:
            # Divide the subparts in diferent parts keeping the other fields
            # (reference, description, ...).
            # First search for the used filed to manufacture/distributor numbers
            # and how many subparts are in them. Use the loop also to extract the
            # manufacture/distributor codes in list.
            founded_fields = []
            subparts_qty = 0
            subparts_manf = dict()
            for field_code in dist:
                if field_code in part:
                    subparts_qty = max(subparts_qty, 
                            len( subpart_list(part[field_code]) ) ) # Quantity of sub parts.
                    founded_fields += [field_code]
                    subparts_manf[field_code] = subpart_list(part[field_code])
            if not founded_fields:
                split_components[part_ref] = part
                continue # If not manf/distributor code pass to next.

            if logger.isEnabledFor(DEBUG_DETAILED):
                print(part_ref, '>>', founded_fields)

            # Second, if more than one subpart, split the sub parts as
            # new components with the same description, footprint, and
            # so on... Get the subpar
            if subparts_qty>1:
                # Remove the actual part from the list.
                part_actual = part
                part_actual_value = part_actual['value']
                # Add the splited subparts.
                for subparts_index in range(subparts_qty):
                    # Create a sub component based on the main component with
                    # the subparts. Modify the designator and the part. Create
                    # a sub quantity field.
                    subpart_actual = part_actual.copy()
                    for field_manf in founded_fields:
                        # For each manufacture/distributor code take the same order of
                        # the code list and split in each subpart. When not founded one
                        # part, do not add.
                        # e.g. U1:{'manf#':'PARTG1;PARTG2;PARTG3', 'mouser#''PARTM1;PARTM2'}
                        # result:
                        # U1.1:{'manf#':'PARTG1', 'mouser#':'PARTM1'}
                        # U1.2:{'manf#':'PARTG2', 'mouser#':'PARTM2'}
                        # U1.3:{'manf#':'PARTG3'}
                        try:
                            p_manf = subparts_manf[field_manf][subparts_index]
                            subpart_qty, subpart_part = subpart_qtypart(p_manf)
                            subpart_actual['value'] = '{v} - p{idx}/{total}'.format(
                                            v=part_actual_value,
                                            idx=subparts_index+1,
                                            total=subparts_qty)
                            subpart_actual[field_manf] = subpart_part
                            subpart_actual[field_manf+'_subqty'] = subpart_qty
                            if logger.isEnabledFor(DEBUG_OBSESSIVE):
                                print(subpart_actual)
                        except IndexError:
                            pass
                    ref = part_ref + SUB_SEPRTR + str(subparts_index + 1)
                    split_components[ref] = subpart_actual
            else:
                split_components[part_ref] = part
        except KeyError:
            continue
    return split_components
    

def subpart_qty(component):
    '''
    Calculate the string of the quantity of the item parsing the
    referente (design) quantity and the sub quantity (in case that
    was a sub part of a manufacture/distributor code).
    '''
    try:
        if logger.isEnabledFor(DEBUG_OBSESSIVE):
            print('Qty>>',component.refs,'>>',
                component.fields.get('manf#_subqty'), '*',
                	component.fields.get('manf#'))

        subqty = component.fields.get('manf#_subqty')
        string = '={{}}*{qty}'.format(qty=len(component.refs))
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



# ------------------ Private functions

def subpart_list(part):
    # Get the list of sub parts manufacture / distributor code
    # numbers stripping the spaces and keeping the sub part
    # quantity information, these have to be separated by
    # PART_SEPRTR definition.
    return re.split('(?<![\W\*\/])\s*' + PART_SEPRTR +
        '\s*|\s*' + PART_SEPRTR + '\s*(?![\W\*\/])',
                part.strip())


def subpart_qtypart(subpart):
    # Get the quantity and the part code of the sub part
    # manufacture / distributor. Test if was pre or post
    # multiplied by a constant.
    # Setting QTY_SEPRTR as '\:', we have
    # ' 4.5 : ADUM3150BRSZ-RL7' -> ('4.5', 'ADUM3150BRSZ-RL7')
    # '4/5  : ADUM3150BRSZ-RL7' -> ('4/5', 'ADUM3150BRSZ-RL7')
    # '7:ADUM3150BRSZ-RL7' -> ('7', 'ADUM3150BRSZ-RL7')
    # 'ADUM3150BRSZ-RL7 :   7' -> ('7', 'ADUM3150BRSZ-RL7')
    # 'ADUM3150BRSZ-RL7' -> ('1', 'ADUM3150BRSZ-RL7')
    # 'ADUM3150BRSZ-RL7:' -> ('1', 'ADUM3150BRSZ-RL7') forgot the qty understood '1'
    strings = re.split('\s*' + QTY_SEPRTR + '\s*', subpart)
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
            if len(re.sub('[\.\/]','',strings[0])) < re.sub('[\.\/]','',len(strings[1])):
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
