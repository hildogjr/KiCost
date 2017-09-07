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
#from ..kicost import field_name_translations
import re # Regular expression parser.

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

__all__ = ['subpart_split','subpart_qty']

QTY_SSTR = '[\:]' # String that separate the subpart quantity and the
                # manufacture/distributor code.
PART_SSTR = '[\;\,]' # String that separate the part (manufacture/
                     # distributor code) in the list.
SUB_SSTR = '.' # String to separete the subpart in the new reference create.

#global field_name_translations # Use the definitions of fileds for
                               # manufacture/distributors code.

# Definitions to parse the manufature / distributor code to allow
# sub parts and diferent quantities (even fraction) in these.



# ------------------ Plublic functions

def subpart_split(components):
    # For each designator...
    designator = list(components.keys())
    for parts_index in range(len(designator)):
        part = components[designator[parts_index]]
        try:
            # Divide the subparts in diferent parts keeping the other fields
            # (reference, description, ...).
            # First search for the used filed to manufacture/distributor numbers
            # and how many subparts are in them. Use the loop also to extract the
            # manufacture/distributor codes in list.
            founded_fields = []
            subparts_qty = 0
            subparts_manf = dict()
            for field_code in ['manf#','digikey#','mouser#']:#field_name_translations.keys():
                if field_code in part:
                    subparts_qty = max(subparts_qty, 
                            len( subpart_list(part[field_code]) ) )
                    founded_fields += [field_code]
                    subparts_manf[field_code] = subpart_list(part[field_code])
            if not founded_fields:
                continue # If not manf/distributor code pass to next.
            # Second, if more than one subpart, split the sub parts as
            # new components with the same description, footprint, and
            # so on... Get the subpar
            if subparts_qty>1:
                # Remove the actual part from the list.
                part_actual = components.pop(designator[parts_index])
                # Add the splited subparts.
                for subparts_index in range(0,subparts_qty):
                    # Create a sub component based on the main component with
                    # the subparts. Modity the designator and the part. Create
                    # a sub quantity field.
                    subpart_actual = part_actual
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
                            subparts_qty, subpart_part = subpart_qtypart(p_manf)
                            subpart_actual[field_manf] = subpart_part
                            subpart_actual[field_manf+'_subqty'] = subparts_qty
                        except IndexError:
                            pass
                    #ref = designator[parts_index] + SUB_SSTR + str(subparts_index + 1)
                    ref = designator[parts_index] + str(subparts_index + 1) #TODO use the bellow in final code, just a test because of some issue in the order rotine.
                    print('INICIAL>>>',ref,':',subpart_actual,'\n\n')
                    components.update({ref:subpart_actual.copy()})
        except KeyError:
            continue
    print('FINAL>>', components)
    return components
    

def subpart_qty(component):
    # Calculate the string of the quantity of the item parsing the
    # referente (design) quantity and the sub quantity (in case that
    # was a sub part of a manufacture/distributor code).
#    print('DEBUG>>>',component)
#    try:
#        if component['manf#_subqty'] != '1':
#            string = '=ceiling({{}}*{subqty}*{qty})'.format(
#                                subqty=component.subqty,
#                                qty=len(component.refs))
#    except KeyError:
    string = '={{}}*{qty}'.format(len(component.refs))
    return string.format('BoardQty')



# ------------------ Private functions

def subpart_list(part):
    # Get the list f sub parts manufacture / distributor code
    # numbers striping the spaces and keeping the sub part
    # quantity information, these have to be separated by
    # PART_SSTR definition.
    return re.split('(?<![\W\*\/])\s*' + PART_SSTR +
        '\s*|\s*' + PART_SSTR + '\s*(?![\W\*\/])',
                part.strip())


def subpart_qtypart(subpart):
    # Get the quantity and the part code of the sub part
    # manufacture / distributor. Test if was pre or post
    # multiplied by a constant.
    # Setting QTY_SSTR as '\:', we have
    # ' 4.5 : ADUM3150BRSZ-RL7' -> ('4.5', 'ADUM3150BRSZ-RL7')
    # '4/5  : ADUM3150BRSZ-RL7' -> ('4/5', 'ADUM3150BRSZ-RL7')
    # '7:ADUM3150BRSZ-RL7' -> ('7', 'ADUM3150BRSZ-RL7')
    # 'ADUM3150BRSZ-RL7 :   7' -> ('7', 'ADUM3150BRSZ-RL7')
    # 'ADUM3150BRSZ-RL7' -> ('1', 'ADUM3150BRSZ-RL7')
    # 'ADUM3150BRSZ-RL7:' -> ('1', 'ADUM3150BRSZ-RL7') forgot the qty understood '1'
    strings = re.split('\s*' + QTY_SSTR + '\s*', subpart)
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
    return qty, part
