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
import logging
import tqdm
import multiprocessing # To deal with the parallel scrape.
from multiprocessing import Pool # For running web scrapes in parallel.

try:
    from urllib.parse import urlsplit, urlunsplit
except ImportError:
    from urlparse import quote as urlsplit, urlunsplit

# Stops UnicodeDecodeError exceptions.
try:
    reload(sys)
    sys.setdefaultencoding('utf8')
except NameError:
    pass  # Happens if reload is attempted in Python 3.

class PartHtmlError(Exception):
    '''Exception for failed retrieval of an HTML parse tree for a part.'''
    pass

# ghost library allows scraping pages that have Javascript challenge pages that
# screen-out robots. Digi-Key stopped doing this, so it's not needed at the moment.
# Also requires installation of Qt4.8 (not 5!) and pyside.
#from ghost import Ghost

__all__ = ['kicost']  # Only export this routine for use by the outside world.

SEPRTR = ':'  # Delimiter between library:component, distributor:field, etc.

logger = logging.getLogger('kicost')
DEBUG_OVERVIEW = logging.DEBUG
DEBUG_DETAILED = logging.DEBUG-1
DEBUG_OBSESSIVE = logging.DEBUG-2

# Import information about various distributors.
from . import distributors as distributor_imports
distributors = distributor_imports.distributors
create_local_part_html = distributor_imports.create_local_part_html
scrape_part = distributor_imports.scrape_part

# Import import functions for various EDA tools.
from . import eda_tools as eda_tools_imports
eda_tools = eda_tools_imports.eda_tools
group_parts = eda_tools_imports.group_parts
from .eda_tools.eda_tools import SUB_SEPRTR
from .spreadsheet import * # Creation of the final XLSX spreadsheet.

def kicost(in_file, out_filename, user_fields, ignore_fields, variant, num_processes, 
        eda_tool_name, exclude_dist_list, include_dist_list, scrape_retries):
    '''Take a schematic input file and create an output file with a cost spreadsheet in xlsx format.'''

    # Only keep distributors in the included list and not in the excluded list.
    if not include_dist_list:
        include_dist_list = list(distributors.keys())
    rmv_dist = set(exclude_dist_list)
    rmv_dist |= set(list(distributors.keys())) - set(include_dist_list)
    rmv_dist -= set(['local_template'])  # Needed later for creating non-web distributors.
    for dist in rmv_dist:
        distributors.pop(dist, None)

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
        eda_tool_module = getattr(eda_tools_imports, eda_tool_name[i_prj])
        p, info = eda_tool_module.get_part_groups(in_file[i_prj], ignore_fields, variant[i_prj])
        # Group part out of the module to merge diferent project lists, ignore some filed to merge, issue #131 and #102 (in the future) #ISSUE.
        p = group_parts(p)
        # Add the project indentifier in the references.
        for i_g in range(len(p)):
            p[i_g].qty = 'Board{}Qty'.format(i_prj) # 'Board{}Qty' string is used to put name quantity cells of the spreadsheet.
        parts += p
        prj_info.append( info.copy() )

    # Create an HTML page containing all the local part information.
    local_part_html = create_local_part_html(parts)
    
    if logger.isEnabledFor(DEBUG_DETAILED):
        pprint.pprint(distributors)

    # Get the distributor product page for each part and scrape the part data.
    logger.log(DEBUG_OVERVIEW, 'Scrape part data for each component group...')
    global scraping_progress
    scraping_progress = tqdm.tqdm(desc='Progress', total=len(parts), unit='part', miniters=1)
    if num_processes <= 1:
        # Scrape data, one part at a time.
        for i in range(len(parts)):
            args = (i, parts[i], distributors, local_part_html, scrape_retries, logger.getEffectiveLevel())
            id, url, part_num, price_tiers, qty_avail = scrape_part(args)
            parts[id].part_num = part_num
            parts[id].url = url
            parts[id].price_tiers = price_tiers
            parts[id].qty_avail = qty_avail
            scraping_progress.update(1)
    else:
        # Create pool of processes to scrape data for multiple parts simultaneously.
        pool = Pool(num_processes)

        # Package part data for passing to each process.
        arg_sets = [(i, parts[i], distributors, local_part_html, scrape_retries, logger.getEffectiveLevel()) for i in range(len(parts))]
        
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