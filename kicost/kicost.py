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
"""
  @package
  KiCost script, also with Graphical User Interface - GUI, under MIT license for generate part-cost spreadsheets for circuit boards developed with KiCad and others EDAs.
  Full manual at https://xesscorp.github.io/KiCost
  Development at https://github.com/xesscorp/KiCost
  KiCost is powered by the Kitspace PartInfo API (https://kitspace.org/). Partinfo hooks into paid-for 3rd party services. If you find KiCost useful please donate to the Kitspace Open Collective to keep the service running. (https://opencollective.com/kitspace).
  
  Command line:
      kicost -i "%I" "%O.xslx"
  Run Graphical User Interface:
      kicost
  Check for help on terminal:
      kicost --help
"""


from __future__ import print_function

# Libraries.
import sys, os
import pprint
import tqdm
from collections import OrderedDict

# Stops UnicodeDecodeError exceptions.
try:
    reload(sys)
    sys.setdefaultencoding('utf8')
except NameError:
    pass  # Happens if reload is attempted in Python 3.

__all__ = ['kicost','output_filename', 'kicost_gui_notdependences']  # Only export this routine for use by the outside world.

from .global_vars import *

# TODO this 2 imports above should be removed. `kicost.py` should just import a single function that deal with all API/Scrapes/local inside
#from .distributors.api_octopart import api_octopart
from .distributors.api_partinfo_kitspace import api_partinfo_kitspace
from .distributors.dist_local_template import dist_local_template
from .distributors.distributor import distributor_class
from .distributors.global_vars import distributors_modules_dict

## Import the KiCost libraries functions.
# Import information for various EDA tools.
from .edas.tools import field_name_translations
from .edas import eda_modules
from .edas.tools import subpartqty_split, group_parts, PRJ_STR_DECLARE, PRJPART_SPRTR
# Import information about various distributors.
from .distributors.distributor import *
from .distributors.global_vars import distributor_dict
# Creation of the final XLSX spreadsheet.
from .spreadsheet import *

def kicost(in_file, eda_name, out_filename,
        user_fields, ignore_fields, group_fields, translate_fields,
        variant,
        dist_list=list(distributor_dict.keys()),
        collapse_refs=True, suppress_cat_url=True, currency=DEFAULT_CURRENCY):
    ''' @brief Run KiCost.
    
    Take a schematic input file and create an output file with a cost spreadsheet in xlsx format.
    
    @param in_file `list(str())` List of the names of the input BOM files.
    @param eda_name `list(str())` of the EDA modules to be used to open the `in_file`list.
    @param out_filename `str()` XLSX output file name.
    @param user_fields `list()` of the user fields to be included on the spreadsheet global part.
    @param ignore_fields `list()` of the fields to be ignored on the read EDA modules.
    @param group_fields `list()` of the fields to be grouped/merged on the function group parts that
    are not grouped by default.
    @param translate_fields `list()` of the fields to translate to translate or remove (if `~` present).
    @param variant `list(str())` of regular expression to the BOM variant of each file in `in_file`.
    @param dist_list `list(str())` to be scraped, if empty will be scraped with all distributors
    modules. If `None`, no web/local distributors will be scraped.
    @param collapse_refs `bool()` Collapse or not the designator references in the spreadsheet.
    Default `True`.
    @param suppress_cat_url `bool()` Suppress the distributors catalogue links into the catalogue code in the spreadsheet.
    Default `True`.
    @param currency `str()` Currency in ISO4217. Default 'USD'.
    '''

    # Add or remove field translations, ignore in case the trying to
    # re-translate default field names.
    if translate_fields:
        if len(translate_fields)%2 == 1:
            raise Exception('Translation fields argument should have an even number of words.')
        for c in range(0, len(translate_fields), 2):
            #field_name_translations.keys(), field_name_translations.values()
            if translate_fields[c] in field_name_translations.values():
                logger.warning("Not possible re-translate \"{}\" to \"{}\", this is used as internal field names.".format(
                        translate_fields[c].lower(), translate_fields[c+1].lower()
                    ))
                continue
            if translate_fields[c+1]!='~':
                field_name_translations.update({translate_fields[c].lower():translate_fields[c+1].lower()})
            else:
                field_name_translations.pop(translate_fields[c].lower(), None)

    # Check the integrity of the user personal fields, this should not
    # be any of the reserved fields.
    # This is checked after the translation `dict` is complete, so an
    # before used name field on the translate dictionary can be used
    # user field.
    user_fields = list(set(user_fields))
    for f in user_fields:
        if f.lower() in field_name_translations.keys():
            logger.warning("\"{f}\" field is a reserved field and can not be used user filed. Try to remove it from internal dictionary using `--translate_filed {f} ~`".format(
                    f=f.lower()
                ))
            user_fields.remove(x)

    # Only keep distributors in the included list and not in the excluded list.
    if dist_list!=None:
        if not dist_list:
            dist_list = list(distributor_dict.keys())
        if not 'local_template' in dist_list:
            dist_list += ['local_template'] # Needed later for creating non-web distributors.
        for d in list(distributor_dict.keys()):
            if not d in dist_list:
                distributor_dict.pop(d, None)
    else:
        for d in list(distributor_dict.keys()):
            distributor_dict.pop(d, None)

    # Deal with some code exception (only one EDA tool or variant
    # informed in the multiple BOM files input).
    if not isinstance(in_file,list):
        in_file = [in_file]
    if not isinstance(variant,list):
        variant = [variant] * len(in_file)
    elif len(variant) != len(in_file):
        variant = [variant[0]] * len(in_file) #Assume the first as default.
    if not isinstance(eda_name,list):
        eda_name = [eda_name] * len(in_file)
    elif len(eda_name) != len(in_file):
        eda_name = [eda_name[0]] * len(in_file) #Assume the first as default.

    # Get groups of identical parts.
    parts = OrderedDict()
    prj_info = list()
    for i_prj in range(len(in_file)):
        eda_module = eda_modules[eda_name[i_prj]]
        p, info = eda_module.get_part_groups(in_file[i_prj], ignore_fields, variant[i_prj])
        p = subpartqty_split(p)
        # In the case of multiple BOM files, add the project prefix identifier
        # to each reference/designator. Use the field 'manf#_qty' to control
        # each quantity goes to each project creating a `list()` with length
        # of number of BOM files. This vector will be used in the `group_parts()`
        # to create groups with elements of same 'manf#' that came for different
        # projects.
        if len(in_file)>1:
            logger.log(DEBUG_OVERVIEW, 'Multi BOMs detected, attaching project identification to references...')
            qty_base = ['0'] * len(in_file) # Base zero quantity vector.
            for p_ref in list(p.keys()):
                try:
                    qty_base[i_prj] = p[p_ref]['manf#_qty']
                except:
                    qty_base[i_prj] = '1'
                p[p_ref]['manf#_qty'] = qty_base.copy()
                p[ PRJ_STR_DECLARE + str(i_prj) + PRJPART_SPRTR + p_ref] = p.pop(p_ref)
        parts.update( p.copy() )
        prj_info.append( info.copy() )

    # Group part out of the module to be possible to merge different
    # project lists, ignore some field to merge given in the `group_fields`.
    FIELDS_SPREADSHEET = ['refs', 'value', 'desc', 'footprint', 'manf', 'manf#']
    FIELDS_MANFCAT = ([d + '#' for d in distributor_dict] + ['manf#'])
    FIELDS_MANFQTY = ([d + '#_qty' for d in distributor_dict] + ['manf#_qty'])
    FIELDS_IGNORE = FIELDS_SPREADSHEET + FIELDS_MANFCAT + FIELDS_MANFQTY + user_fields + ['pricing']
    for ref, fields in list(parts.items()):
        for f in fields:
            # Merge all extra fields that read on the files that will
            # not be displayed (Needed to check `user_fields`).
            if f not in FIELDS_IGNORE and SEPRTR not in f and not f in group_fields:
                # Not include repetitive field names or fields with the separator `:` defined on `SEPRTR`.
                group_fields += [f]

    # Some fields to be merged on specific EDA are enrolled bellow.
    if 'kicad' in eda_name:
        group_fields += ['libpart'] # This field may be a mess on multiple sheet designs.
    if len(set(eda_name))>2:
        # If more than one EDA software was used, ignore the 'footprint'
        # field, because they could have different libraries names.
        group_fields += ['footprint']
    group_fields += ['desc', 'var'] # Always ignore 'desc' ('description')
                                    # and 'var' ('variant') fields, merging
                                    # the components in groups.
    group_fields = set(group_fields)
    parts = group_parts(parts, group_fields)

    # If do not have the manufacture code 'manf#' and just distributors codes,
    # check if is asked to scrape a distributor that do not have any code in the
    # parts so, exclude this distributors for the scrap list. This decrease the
    # warning messages given during the process.
    all_fields = []
    for p in parts:
        all_fields += list(p.fields.keys())
    all_fields = set(all_fields)
    if not 'manf#' in all_fields:
        dist_not_rmv = [d for d in distributor_dict.keys() if d+'#' in all_fields]
        dist_not_rmv += ['local_template'] # Needed later for creating non-web distributors.
        #distributor_scrap = {d:distributor_dict[d] for d in dist_not_rmv}
        distributors = distributor_dict.copy().keys()
        for d in distributors:
            if not d in dist_not_rmv:
                logger.warning("No 'manf#' and '%s#' field in any part: no information by '%s'.",
                                d, distributor_dict[d]['label']['name'])
                distributor_dict.pop(d, None)

    if logger.isEnabledFor(DEBUG_DETAILED):
        pprint.pprint(distributor_dict)

    # Get the distributor pricing/qty/etc for each part.
    if dist_list:
        # Set part info to default blank values for all the distributors.
        for part in parts: ## TODO create this for just the current active distributor inside each module.
            # These bellow variable are all the data the each distributor/local API/scrap module needs to fill.
            part.part_num = {dist: '' for dist in dist_list} # Distributor catalogue number.
            part.url = {dist: '' for dist in dist_list} # Purchase distributor URL for the specific part.
            part.price_tiers = {dist: {} for dist in dist_list} # Price break tiers; [[qty1, price1][qty2, price2]...]
            part.qty_avail = {dist: None for dist in dist_list} # Available quantity.
            part.qty_increment = {dist: None for dist in dist_list}
            part.info_dist = {dist: {} for dist in dist_list}
            part.currency = {dist: DEFAULT_CURRENCY for dist in dist_list} # Default currency.
            part.moq = {dist: None for dist in dist_list} # Minimum order quantity allowed by the distributor.
        #distributor.get_dist_parts_info(parts, distributor_dict, dist_list, currency)
        #TODO The calls bellow should became the call above of just one function in the `distributors` package/folder.
        #distributor_class.get_dist_parts_info(parts, distributor_dict, currency) #TODOlocal_template.query_part_info(parts, distributor_dict, currency)
        dist_local_template.query_part_info(parts, distributor_dict, currency)
        api_partinfo_kitspace.query_part_info(parts, distributor_dict, currency)

    # Create the part pricing spreadsheet.
    create_spreadsheet(parts, prj_info, out_filename, currency, collapse_refs, suppress_cat_url,
                      user_fields, '-'.join(variant) if len(variant)>1 else variant[0])

    # Print component groups for debugging purposes.
    if logger.isEnabledFor(DEBUG_DETAILED):
        for part in parts:
            for f in dir(part):
                if f.startswith('__'):
                    continue
                elif f.startswith('html_trees'):
                    continue
                else:
                    print('{} = '.format(f), end=' ')
                    try:
                        pprint.pprint(part.__dict__[f])
                    except TypeError:
                        # Python 2.7 pprint has some problem ordering None and strings.
                        print(part.__dict__[f])
                    except KeyError:
                        pass
            print()




FILE_OUTPUT_MAX_NAME = 10 # Maximum length of the name of the spreadsheet output
                          # generate, this is used in the multifiles to limit the
                          # automatic name generation.
FILE_OUTPUT_MIN_INPUT = 5 # Minimum length of characters to use of the input files
                          # to create the name of the spreadsheet output file. This
                          # is used in the multifile BoM and have prioritize in the
                          # `FILE_OUTPUT_MAX_NAME` definition.
FILE_OUTPUT_INPUT_SEP = '-' # Separator in the name of the output spreadsheet file
                            # when used multiple input file to generate automatically
                            # the name.
# Here because is used at `__main__.py` and `kicost_gui.py`.
def output_filename(files_input):
    ''' @brief Compose a name with the multiple BOM input file names.
    Compose a name with the multiple BOM input file names, limiting to,
    at least, the first `FILE_OUTPUT_MIN_INPUT` characters of each name
    (avoid huge names by `FILE_OUTPUT_MAX_NAME`definition). Join the names
    of the input files by `FILE_OUTPUT_INPUT_SEP` definition.
    The output folder is the folder of the first file.
    @param files_input `list()`of the input file names.
    @return `str()` file name for the spreadsheet.
    '''

    if len(files_input)==1:
        # Use the folder of the project.
        return os.path.splitext(files_input[0])[0] + '.xlsx'
    else:
        # If more the one file selected, check if they are in
        # the same folder, if don't, output in the folder where
        # `kicost` was called.
        dir_output = os.path.dirname(files_input[0]) + os.path.sep
        for dir_idx in range(len(files_input)):
            if os.path.dirname(files_input[dir_idx])!=dir_output:
                dir_output = os.getcwd()

    file_name = FILE_OUTPUT_INPUT_SEP.join( [ os.path.splitext(os.path.basename(input_name))[0][:max(int(FILE_OUTPUT_MAX_NAME/len(files_input)),FILE_OUTPUT_MIN_INPUT-len(FILE_OUTPUT_INPUT_SEP))] for input_name in files_input ] )
    file_output = os.path.join(dir_output, file_name + '.xlsx')
    return file_output

def kicost_gui_notdependences():
    print('You don\'t have the wxPython dependence to run the GUI interface. Run once of the follow commands in terminal to install them:')
    print('pip3 install -U wxPython # For Windows & macOS')

    print('pip install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-16.04 wxPython # For Linux 16.04')
    print('Or download from last version from <https://wxpython.org/pages/downloads/>')
    sys.exit(1)
