# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo G Jr
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
from builtins import zip, range, int, str
from future import standard_library
standard_library.install_aliases()
import future

import sys, os
import pprint
import tqdm
from time import time
from multiprocessing import Pool, Manager, Lock

# Stops UnicodeDecodeError exceptions.
try:
    reload(sys)
    sys.setdefaultencoding('utf8')
except NameError:
    pass  # Happens if reload is attempted in Python 3.

# ghost library allows scraping pages that have Javascript challenge pages that
# screen-out robots. Digi-Key stopped doing this, so it's not needed at the moment.
# Also requires installation of Qt4.8 (not 5!) and pyside.
#from ghost import Ghost

__all__ = ['kicost','output_filename_multipleinputs']  # Only export this routine for use by the outside world.

from .globals import *

# Import information about various distributors.
from .distributors import distributor_dict
from .distributors.web_routines import scrape_part
from .distributors.local.local import create_part_html as create_local_part_html

# Import information for various EDA tools.
from .eda_tools import eda_modules
from .eda_tools.eda_tools import subpartqty_split, group_parts

from .spreadsheet import * # Creation of the final XLSX spreadsheet.

def kicost(in_file, eda_tool_name, out_filename,
        user_fields, ignore_fields, group_fields, variant,
        dist_list=list(distributor_dict.keys()),
        num_processes=4, scrape_retries=5, throttling_delay=0.0, collapse_refs=True):
    ''' @brief Run KiCost.
    
    Take a schematic input file and create an output file with a cost spreadsheet in xlsx format.
    
    @param in_file `list(str())` List of the names of the input BOM files.
    @param eda_tool_name `list(str())` of the EDA modules to be used to open the `in_file`list.
    @param out_filename `str()` XLSX output file name.
    @param user_fields `list()` of the user fields to be included on the spreadsheet global part.
    @param ignore_fields `list()` of the fields to be ignored on the read EDA modules.
    @param group_fields `list()` of the fields to be groupd/merged on the function group parts that
    are not grouped by default.
    @param variant `list(str())` of regular expression to the BOM variant of each file in `in_file`.
    @param dist_list `list(str())` to be scraped, if empty will be scraped with all distributors
    modules. If `None`, no web/local distributors will be scraped.
    @param num_processes `int()` Number of parallel processes used for web scraping part data. Use
    1 for serial mode.
    @param scrape_retries `int()` Number of attempts to retrieve part data from a website..
    @param throttling_delay `float()` Minimum delay (in seconds) between successive accesses to a
    distributor's website.
    @param collapse_refs `bool()` Collapse or not the designator references in the spreadsheet.
    Default `True`.
    '''

    # Only keep distributors in the included list and not in the excluded list.
    if dist_list!=None:
        if not dist_list:
            print('YES')
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
    if not isinstance(eda_tool_name,list):
        eda_tool_name = [eda_tool_name] * len(in_file)
    elif len(eda_tool_name) != len(in_file):
        eda_tool_name = [eda_tool_name[0]] * len(in_file) #Assume the first as default.

    # Get groups of identical parts.
    parts = dict()
    prj_info = list()
    for i_prj in range(len(in_file)):
        eda_tool_module = eda_modules[eda_tool_name[i_prj]]
        p, info = eda_tool_module.get_part_groups(in_file[i_prj], ignore_fields, variant[i_prj])
        p = subpartqty_split(p)
        # In the case of multiple BOM files, add the project prefix
        # identifier to each reference/designator. Use the field
        # 'manf#_qty' to control each quantity goes to each project
        # creating a `list()` with length of number of BOM files.
        # This vector will be used in the `group_parts()` to create
        # groups with elements of same 'manf#' that came for different
        # projects.
        if len(in_file)>1:
            logger.log(DEBUG_OVERVIEW, 'Multi BOMs detected, attaching project indentificator to references...')
            qty_base = ['0'] * len(in_file) # Base zero quantity vetor.
            for p_ref in list(p.keys()):
                try:
                    qty_base[i_prj] = p[p_ref]['manf#_qty']
                except:
                    qty_base[i_prj] = '1'
                p[p_ref]['manf#_qty'] = qty_base.copy()
                p[ 'prj' + str(i_prj) + SEPRTR + p_ref] = p.pop(p_ref)
        parts.update( p.copy() )
        prj_info.append( info.copy() )
    # Group part out of the module to merge different project lists,
    # ignore some field to merge.
    parts = group_parts(parts, group_fields)

    # If do not have the manufacture code 'manf#' and just distributors codes,
    # check if is asked to scrap a distributor that do not have any code in the
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
                logger.warning("No 'manf#' and '%s#' field in any part: distributor '%s' will be not scraped.", d, distributor_dict[d]['label'])
                distributor_dict.pop(d, None)

    # Create an HTML page containing all the local part information.
    local_part_html = create_local_part_html(parts, distributor_dict)
    
    if logger.isEnabledFor(DEBUG_DETAILED):
        pprint.pprint(distributor_dict)

    # Set the throttling delay for each distributor.
    for d in distributor_dict:
        distributor_dict[d]['throttling_delay'] = throttling_delay

    # Get the distributor product page for each part and scrape the part data.
    if dist_list:
        logger.log(DEBUG_OVERVIEW, 'Scraping part data for each component group...')

        global scraping_progress
        scraping_progress = tqdm.tqdm(desc='Progress', total=len(parts), unit='part', miniters=1)

        if num_processes <= 1:
            # Scrape data, one part at a time using single processing.

            class DummyLock:
                """Dummy synchronization lock used when single processing."""
                def __init__(self):
                    pass
                def acquire(*args, **kwargs):
                    return True  # Lock can ALWAYS be acquired when just one process is running.
                def release(*args, **kwargs):
                    pass

            # Create sync lock and timeouts to control the rate at which distributor
            # websites are scraped.
            throttle_lock = DummyLock()
            throttle_timeouts = dict()
            throttle_timeouts = {d:time() for d in distributor_dict}

            for i in range(len(parts)):
                args = (i, parts[i], distributor_dict, local_part_html, scrape_retries,
                        logger.getEffectiveLevel(), throttle_lock, throttle_timeouts)
                id, url, part_num, price_tiers, qty_avail = scrape_part(args)
                parts[id].part_num = part_num
                parts[id].url = url
                parts[id].price_tiers = price_tiers
                parts[id].qty_avail = qty_avail
                scraping_progress.update(1)
        else:
            # Scrape data, multiple parts at a time using multiprocessing.

            # Create sync lock and timeouts to control the rate at which distributor
            # websites are scraped.
            throttle_manager = Manager()  # Manages shared lock and dict.
            throttle_lock = throttle_manager.Lock()
            throttle_timeouts = throttle_manager.dict()
            for d in distributor_dict:
                throttle_timeouts[d] = time()

            # Create pool of processes to scrape data for multiple parts simultaneously.
            pool = Pool(num_processes)

            # Package part data for passing to each process.
            arg_sets = [(i, parts[i], distributor_dict, local_part_html, scrape_retries, 
                        logger.getEffectiveLevel(), throttle_lock, throttle_timeouts) for i in range(len(parts))]
            
            # Define a callback routine for updating the scraping progress bar.
            def update(x):
                scraping_progress.update(1)
                return x

            # Start the web scraping processes, one for each part.
            logger.log(DEBUG_OVERVIEW, 'Starting {} parallels process...'.format(num_processes))
            results = [pool.apply_async(scrape_part, [args], callback=update) for args in arg_sets]

            # Wait for all the processes to have results, then kill-off all the scraping processes.
            for r in results:
                while(not r.ready()):
                    pass
            logger.log(DEBUG_OVERVIEW, 'All parallels process finished with success.')
            pool.close()
            pool.join()

            # Get the data from each process result structure.
            logger.log(DEBUG_OVERVIEW, 'Getting the part scraped informations...')
            for result in results:
                id, url, part_num, price_tiers, qty_avail = result.get()
                parts[id].part_num = part_num
                parts[id].url = url
                parts[id].price_tiers = price_tiers
                parts[id].qty_avail = qty_avail

        # Done with the scraping progress bar so delete it or else we get an 
        # error when the program terminates.
        del scraping_progress

    # Create the part pricing spreadsheet.
    create_spreadsheet(parts, prj_info, out_filename, collapse_refs,
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
                        # Pyton 2.7 pprint has some problem ordering None and strings.
                        print(part.__dict__[f])
                    except KeyError:
                        pass
            print()




FILE_OUTPUT_MAX_NAME = 10 # Maximum length of the name of the spreadsheet output
                          # generate, this is used in the multifiles to limit the
                          # automatic name generation.
FILE_OUTPUT_MIN_INPUT = 5 # Minimum length of characters to use of the input files
                          # to create the name of the spreadsheet output file. This
                          # is used in the multifile BoM and have priorite in the
                          # `FILE_OUTPUT_MAX_NAME` definition.
FILE_OUTPUT_INPUT_SEP = '-' # Separator in the name of the output spreadsheet file
                            # when used multiple input file to generate automatically
                            # the name.
# Here because is used at `__main__.py` and `kicost_gui.py`.
def output_filename_multipleinputs(files_input):
    ''' @brief Compose a name with the multiple BOM input file names.
    
    Compose a name with the multiple BOM input file names, limiting to,
    at least, the first `FILE_OUTPUT_MIN_INPUT` caracheters of each name
    (avoid huge names by `FILE_OUTPUT_MAX_NAME`definition). Join the names
    of the input files by `FILE_OUTPUT_INPUT_SEP` definition.
    The output folder is the folder of the firt file.
    @param files_input `list()`of the input file names.
    @return `str()` file name for the spreadsheet.
    '''
    file_output = os.path.dirname(files_input[0]) + os.path.sep
    file_output += FILE_OUTPUT_INPUT_SEP.join( [ os.path.splitext(os.path.basename(input_name))[0][:max(int(FILE_OUTPUT_MAX_NAME/len(files_input)),FILE_OUTPUT_MIN_INPUT-len(FILE_OUTPUT_INPUT_SEP))] for input_name in files_input ] ) + '.xlsx'
    return file_output
