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

import sys
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

__all__ = ['kicost']  # Only export this routine for use by the outside world.

from .globals import *

# Import information about various distributors.
from .distributors import distributor_dict
from .distributors.web_routines import scrape_part, create_local_part_html

# Import information for various EDA tools.
from .eda_tools import eda_modules
from .eda_tools.eda_tools import group_parts

from .spreadsheet import * # Creation of the final XLSX spreadsheet.


def kicost(in_file, out_filename, user_fields, ignore_fields, group_fields, variant, num_processes, 
        eda_tool_name, exclude_dist_list, include_dist_list, scrape_retries, throttling_delay=0.0):
    '''Take a schematic input file and create an output file with a cost spreadsheet in xlsx format.'''

    # Only keep distributors in the included list and not in the excluded list.
    if not include_dist_list:
        include_dist_list = list(distributor_dict.keys())
    rmv_dist = set(exclude_dist_list)
    rmv_dist |= set(list(distributor_dict.keys())) - set(include_dist_list)
    rmv_dist -= set(['local_template'])  # Needed later for creating non-web distributors.
    for dist in rmv_dist:
        distributor_dict.pop(dist, None)

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
    parts = list()
    prj_info = list()
    for i_prj in range(len(in_file)):
        #eda_tool_module = getattr(eda_tools, eda_tool_name[i_prj])
        eda_tool_module = eda_modules[eda_tool_name[i_prj]]
        p, info = eda_tool_module.get_part_groups(in_file[i_prj], ignore_fields, variant[i_prj])
        # Group part out of the module to merge different project lists, ignore some filed to merge, issue #131 and #102 (in the future). Next step, move the call of the function out of this loop and finish #73 implementation, remove `ignore_fields` of the call in the function above. #ISSUE.
        p = group_parts(p, group_fields)
        # Add the project identifier in the references.
        for i_g in range(len(p)):
            p[i_g].qty = 'Board{}Qty'.format(i_prj) # 'Board{}Qty' string is used to put name quantity cells of the spreadsheet.
        parts += p
        prj_info.append( info.copy() )

    # Create an HTML page containing all the local part information.
    local_part_html = create_local_part_html(parts, distributor_dict)
    
    if logger.isEnabledFor(DEBUG_DETAILED):
        pprint.pprint(distributor_dict)

    # Set the throttling delay for each distributor.
    for d in distributor_dict:
        distributor_dict[d]['throttling_delay'] = throttling_delay

    # Get the distributor product page for each part and scrape the part data.
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
        results = [pool.apply_async(scrape_part, [args], callback=update) for args in arg_sets]

        # Wait for all the processes to have results, then kill-off all the scraping processes.
        for r in results:
            while(not r.ready()):
                pass
        pool.close()
        pool.join()

        # Get the data from each process result structure.
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
    create_spreadsheet(parts, prj_info, out_filename, user_fields,
                       '-'.join(variant) if len(variant)>1 else variant[0])

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
