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
  KiCost script, also with Graphical User Interface - GUI, under MIT license for generate part-cost spreadsheets for circuit boards developed with KiCad and
  others EDAs.
  Full manual at https://xesscorp.github.io/KiCost
  Development at https://github.com/xesscorp/KiCost
  KiCost is powered by the Kitspace PartInfo API (https://kitspace.org/). Partinfo hooks into paid-for 3rd party services. If you find KiCost useful please
  donate to the Kitspace Open Collective to keep the service running. (https://opencollective.com/kitspace).

  Command line:
      kicost -i "%I" "%O.xslx"
  Run Graphical User Interface:
      kicost
  Check for help on terminal:
      kicost --help
"""


# Libraries.
import sys
import os
import pprint
from collections import OrderedDict
from copy import copy
from math import ceil

# Stops UnicodeDecodeError exceptions.
try:
    reload(sys)
    sys.setdefaultencoding('utf8')
except NameError:
    pass  # Happens if reload is attempted in Python 3.

# Only export this routine for use by the outside world.
__all__ = ['kicost', 'output_filename', 'kicost_gui_notdependences', 'query_part_info']

from .global_vars import DEFAULT_CURRENCY, SEPRTR, DEF_MAX_COLUMN_W, ERR_KICOSTCONFIG, ERR_ARGS, W_TRANS, W_NOMANP
# * Import the KiCost libraries functions.
# Import information for various EDA tools.
from .edas.tools import field_name_translations, subpartqty_split, group_parts, PRJ_STR_DECLARE, PRJPART_SPRTR, partgroup_qty
from .edas import get_part_groups
# Creation of the final XLSX spreadsheet.
from .spreadsheet import create_spreadsheet, Spreadsheet
# Import the scrape API
from .distributors import get_dist_parts_info, get_registered_apis, get_distributors_iter, get_distributor_info
from . import debug_detailed, debug_overview, is_debug_detailed, is_debug_overview, error, warning, KiCostError


def query_part_info(parts, dist_list, currency=DEFAULT_CURRENCY):
    """ Used to get the parts price and information.
        Also used from outside KiCost. """
    if is_debug_overview():
        api_list = [d.name + ('(Disabled)' if not d.enabled else '') for d in get_registered_apis()]
        debug_overview('Scrape API list ' + str(api_list))
    get_dist_parts_info(parts, dist_list, currency)


def solve_parts_qtys(parts, multi_prj, prj_info):
    """ Used to fill the qty_str, qty and qty_total_spreadsheet members of the parts.
        Also used from outside KiCost. """
    for part in parts:
        part.qty_str, part.qty = partgroup_qty(part)
        # Total for all boards
        if multi_prj:
            total = 0
            for i_prj, p_info in enumerate(prj_info):
                total += part.qty[i_prj] * p_info['qty']
        else:
            total = part.qty * prj_info[0]['qty']
        part.qty_total_spreadsheet = ceil(total)


def kicost(in_file, eda_name, out_filename, user_fields, ignore_fields, group_fields, translate_fields, variant, dist_list, collapse_refs=True,
           suppress_cat_url=True, currency=DEFAULT_CURRENCY, max_column_width=DEF_MAX_COLUMN_W, split_extra_fields=[],
           board_qty=[Spreadsheet.DEFAULT_BUILD_QTY]):
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
    @param dist_list `list(str())` to be scraped
    modules. If `None`, no web/local distributors will be scraped.
    @param collapse_refs `bool()` Collapse or not the designator references in the spreadsheet.
    Default `True`.
    @param suppress_cat_url `bool()` Suppress the distributors catalogue links into the catalogue code in the spreadsheet.
    Default `True`.
    @param currency `str()` Currency in ISO4217. Default 'USD'.
    @param max_column_width `int()` The maximum column width. If 0 disables cell size adjust. Default: DEF_MAX_COLUMN_W
    @param split_extra_fields `list(str())` Fields that will be split using the multipart mechanism.
    @param board_qty `list(int())` Board quantities for each project.
    '''
    # Add or remove field translations, ignore in case the trying to
    # re-translate default field names.
    if translate_fields:
        if len(translate_fields) % 2 == 1:
            raise KiCostError('Translation fields argument should have an even number of words.', ERR_ARGS)
        for c in range(0, len(translate_fields), 2):
            # field_name_translations.keys(), field_name_translations.values()
            if translate_fields[c] in field_name_translations.values():
                warning(W_TRANS, "Unable to re-translate \"{}\" to \"{}\", this is used as an internal field name.".
                        format(translate_fields[c].lower(), translate_fields[c+1].lower()))
                continue
            if translate_fields[c+1] != '~':
                field_name_translations.update({translate_fields[c].lower(): translate_fields[c+1].lower()})
            else:
                field_name_translations.pop(translate_fields[c].lower(), None)

    # Check the integrity of the user personal fields, this should not
    # be any of the reserved fields.
    # This is checked after the translation `dict` is complete, so an
    # before used name field on the translate dictionary can be used
    # user field.
    user_fields = list(OrderedDict([(lv, 1) for lv in user_fields]))  # Avoid repeated fields
    for f in user_fields:
        if f.lower() in field_name_translations:
            warning(W_TRANS, "\"{f}\" field is a reserved field and can not be used as user field."
                    " Try to remove it from internal dictionary using `--translate_fields {f} ~`".format(f=f.lower()))
            user_fields.remove(f)

    c_files = len(in_file)
    # Deal with some code exception (only one EDA tool or variant
    # informed in the multiple BOM files input).
    # This code is never used when called from __main__
    if not isinstance(in_file, list):
        in_file = [in_file]
    if not isinstance(variant, list):
        variant = [variant] * c_files
    elif len(variant) != c_files:
        variant = [variant[0]] * c_files  # Assume the first as default.
    if not isinstance(eda_name, list):
        eda_name = [eda_name] * c_files
    elif len(eda_name) != c_files:
        eda_name = [eda_name[0]] * c_files  # Assume the first as default.
    if not isinstance(board_qty, list):
        board_qty = [board_qty] * c_files
    elif len(board_qty) != c_files:
        board_qty = [board_qty[0]] * c_files  # Assume the first as default.

    # Get groups of identical parts.
    parts = OrderedDict()
    prj_info = list()
    for i_prj in range(c_files):
        p, info = get_part_groups(eda_name[i_prj], in_file[i_prj], ignore_fields, variant[i_prj], dist_list)
        p = subpartqty_split(p, dist_list, split_extra_fields)
        if c_files > 1:
            # In the case of multiple BOM files, add the project prefix identifier
            # to each reference/designator. Use the field 'manf#_qty' to set
            # the quantity for each project, creating a `list()` with length
            # of number of BOM files. This vector will be used in the `group_parts()`
            # to create groups with elements of same 'manf#' that came from different
            # projects.
            debug_overview('Multi BOMs detected, attaching project identification to references...')
            qty_base = ['0'] * c_files  # Zero for all projects
            for p_ref, p_fields in p.items():
                # Copy the qty to the position corresponding to this project
                qty_base[i_prj] = p_fields.get('manf#_qty', '1')
                p_fields['manf#_qty'] = copy(qty_base)
                parts[PRJ_STR_DECLARE + str(i_prj) + PRJPART_SPRTR + p_ref] = p_fields
        else:
            parts.update(p)
        info['qty'] = board_qty[i_prj]
        prj_info.append(info)

    # Group part out of the module to be possible to merge different
    # project lists, ignore some field to merge given in the `group_fields`.
    FIELDS_SPREADSHEET = ['refs', 'value', 'desc', 'footprint', 'manf', 'manf#']
    FIELDS_MANFCAT = ([d + '#' for d in get_distributors_iter()] + ['manf#'])
    FIELDS_MANFQTY = ([d + '#_qty' for d in get_distributors_iter()] + ['manf#_qty'])
    FIELDS_IGNORE = FIELDS_SPREADSHEET + FIELDS_MANFCAT + FIELDS_MANFQTY + user_fields + ['pricing']
    for ref, fields in list(parts.items()):
        for f in fields:
            # Merge all extra fields that read on the files that will
            # not be displayed (Needed to check `user_fields`).
            if f not in FIELDS_IGNORE and SEPRTR not in f and f not in group_fields:
                # Not include repetitive field names or fields with the separator `:` defined on `SEPRTR`.
                group_fields += [f]

    # Some fields to be merged on specific EDA are enrolled bellow.
    if 'kicad' in eda_name:
        group_fields += ['libpart']  # This field may be a mess on multiple sheet designs.
    if len(set(eda_name)) > 2:
        # If more than one EDA software was used, ignore the 'footprint'
        # field, because they could have different libraries names.
        group_fields += ['footprint']
    # Always ignore 'desc' ('description') and 'var' ('variant') fields, merging the components in groups.
    group_fields += ['desc', 'var']
    group_fields = set(group_fields)
    parts = group_parts(parts, group_fields, c_files)

    # If do not have the manufacture code 'manf#' and just distributors codes,
    # check if is asked to scrape a distributor that do not have any code in the
    # parts so, exclude this distributors for the scrap list. This decrease the
    # warning messages given during the process.
    all_fields = set()
    for p in parts:
        all_fields.update(p.fields)
    if 'manf#' not in all_fields:
        new_list = []
        for d in dist_list:
            if d+'#' not in all_fields:
                warning(W_NOMANP, "No 'manf#' and '{}#' field in any part: no information by '{}'.".
                        format(d, get_distributor_info(d).label.name))
            else:
                new_list.append(d)
        dist_list = new_list
    # Debug the resulting list
    if is_debug_detailed():
        debug_detailed('Distributors: ' + pprint.pformat(dist_list))
    #
    # Solve the quantity for each group
    #
    # Make sure we have the number of boards for each project
    for p_info in prj_info:
        if 'qty' not in p_info:
            p_info['qty'] = Spreadsheet.DEFAULT_BUILD_QTY
    multi_prj = len(prj_info) > 1
    # Compute the qtys
    solve_parts_qtys(parts, multi_prj, prj_info)
    # Get the distributor pricing/etc for each part.
    query_part_info(parts, dist_list, currency)

    # Create the part pricing spreadsheet.
    create_spreadsheet(parts, prj_info, out_filename, dist_list, currency, collapse_refs, suppress_cat_url,
                       user_fields, '-'.join(variant) if len(variant) > 1 else variant[0], max_column_width)

    # Print component groups for debugging purposes.
    if is_debug_detailed():
        for part in parts:
            for f in dir(part):
                if f.startswith('__'):
                    continue
                elif f.startswith('html_trees'):
                    continue
                else:
                    head = '{} = '.format(f)
                    try:
                        debug_detailed(head + pprint.pformat(part.__dict__[f]))
                    except TypeError:
                        # Python 2.7 pprint has some problem ordering None and strings.
                        debug_detailed(head + str(part.__dict__[f]))
                    except KeyError:
                        pass
            debug_detailed('')


# Maximum length of the name of the spreadsheet output generate, this is used in the multifiles to limit the
# automatic name generation.
FILE_OUTPUT_MAX_NAME = 10
# Minimum length of characters to use of the input files to create the name of the spreadsheet output file.
# This is used in the multifile BoM and have prioritize in the `FILE_OUTPUT_MAX_NAME` definition.
FILE_OUTPUT_MIN_INPUT = 5
# Separator in the name of the output spreadsheet file when used multiple input file to generate automatically
# the name.
FILE_OUTPUT_INPUT_SEP = '-'


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

    if len(files_input) == 1:
        # Use the folder of the project.
        return os.path.splitext(files_input[0])[0] + '.xlsx'
    else:
        # If more the one file selected, check if they are in
        # the same folder, if don't, output in the folder where
        # `kicost` was called.
        dir_output = os.path.dirname(files_input[0]) + os.path.sep
        for dir_idx in range(len(files_input)):
            if os.path.dirname(files_input[dir_idx]) != dir_output:
                dir_output = os.getcwd()

    _end = max(int(FILE_OUTPUT_MAX_NAME/len(files_input)), FILE_OUTPUT_MIN_INPUT-len(FILE_OUTPUT_INPUT_SEP))
    file_name = FILE_OUTPUT_INPUT_SEP.join([os.path.splitext(os.path.basename(input_name))[0][:_end] for input_name in files_input])
    file_output = os.path.join(dir_output, file_name + '.xlsx')
    return file_output


def kicost_gui_notdependences():
    error('You don\'t have the wxPython dependence to run the GUI interface.')
    error('Run once of the following commands in a terminal to install it:')
    error('pip3 install -U wxPython # For Windows & macOS')
    error('sudo apt-get install python3-wxgtk4.0 # Modern Linux derived from Debian, like Ubuntu')
    error('pip install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-16.04 wxPython # For Linux 16.04')
    error('Or download the last version from <https://wxpython.org/pages/downloads/>')
    sys.exit(ERR_KICOSTCONFIG)
