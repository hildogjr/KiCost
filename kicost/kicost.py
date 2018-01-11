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
import copy
import logging, pprint
from bs4 import BeautifulSoup # XML file interpreter.
from yattag import Doc, indent  # For generating HTML page for local parts.
import multiprocessing, tqdm
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

# Import import functions for various EDA tools.
from . import eda_tools as eda_tools_imports
eda_tools = eda_tools_imports.eda_tools
group_parts = eda_tools_imports.group_parts
from .eda_tools.eda_tools import SUB_SEPRTR

# Regular expression for detecting part reference ids consisting of a
# prefix of letters followed by a sequence of digits, such as 'LED10'
# or a sequence of digits followed by a subpart number like 'CONN1#3'.
# There can even be an interposer character so 'LED-10' is also OK.
#PART_REF_REGEX = re.compile('(?P<prefix>[a-z]+\W?)(?P<num>((?P<ref_num>\d+)({}(?P<subpart_num>\d+))?))'.format(SUB_SEPRTR), re.IGNORECASE)
#from .eda_tools.eda_tools import PART_REF_REGEX

from .spreadsheet import *

def kicost(in_file, out_filename, user_fields, ignore_fields, variant, num_processes, 
        eda_tool_name, exclude_dist_list, include_dist_list, scrape_retries):
    '''Take a schematic input file and create an output file with a cost spreadsheet in xlsx format.'''

    # Only keep distributors in the included list and not in the excluded list.
    if not include_dist_list:
        include_dist_list = list(distributors.keys())
    rmv_dist = set(exclude_dist_list)
    rmv_dist |= set(list(distributors.keys())) - set(include_dist_list)
    rmv_dist -= set(['local_template'])  # We need this later for creating non-web distributors.
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


def create_local_part_html(parts):
    '''Create HTML page containing info for local (non-webscraped) parts.'''

    global distributors
    
    logger.log(DEBUG_OVERVIEW, 'Create HTML page for parts with custom pricing...')
    
    doc, tag, text = Doc().tagtext()
    with tag('html'):
        with tag('body'):
            for p in parts:
                # Find the manufacturer's part number if it exists.
                pn = p.fields.get('manf#') # Returns None if no manf# field.

                # Find the various distributors for this part by
                # looking for leading fields terminated by SEPRTR.
                for key in p.fields:
                    try:
                        dist = key[:key.index(SEPRTR)]
                    except ValueError:
                        continue

                    # If the distributor is not in the list of web-scrapable distributors,
                    # then it's a local distributor. Copy the local distributor template
                    # and add it to the table of distributors.
                    if dist not in distributors:
                        distributors[dist] = copy.copy(distributors['local_template'])
                        distributors[dist]['label'] = dist  # Set dist name for spreadsheet header.

                # Now look for catalog number, price list and webpage link for this part.
                for dist in distributors:
                    cat_num = p.fields.get(dist+':cat#')
                    pricing = p.fields.get(dist+':pricing')
                    link = p.fields.get(dist+':link')
                    if cat_num is None and pricing is None and link is None:
                        continue

                    def make_random_catalog_number(p):
                        hash_fields = {k: p.fields[k] for k in p.fields}
                        hash_fields['dist'] = dist
                        return '#{0:08X}'.format(abs(hash(tuple(sorted(hash_fields.items())))))

                    cat_num = cat_num or pn or make_random_catalog_number(p)
                    p.fields[dist+':cat#'] = cat_num # Store generated cat#.
                    with tag('div', klass=dist+SEPRTR+cat_num):
                        with tag('div', klass='cat#'):
                            text(cat_num)
                        if pricing is not None:
                            with tag('div', klass='pricing'):
                                text(pricing)
                        if link is not None:
                            url_parts = list(urlsplit(link))
                            if url_parts[0] == '':
                                url_parts[0] = u'http'
                            link = urlunsplit(url_parts)
                            with tag('div', klass='link'):
                                text(link)

    # Remove the local distributor template so it won't be processed later on.
    # It has served its purpose.
    del distributors['local_template']

    html = doc.getvalue()
    if logger.isEnabledFor(DEBUG_OBSESSIVE):
        print(indent(html))
    return html


def get_part_html_tree(part, dist, get_html_tree_func, local_part_html, scrape_retries, logger):
    '''Get the HTML tree for a part from the given distributor website or local HTML.'''

    logger.log(DEBUG_OBSESSIVE, '%s %s', dist, str(part.refs))

    for extra_search_terms in set([part.fields.get('manf', ''), '']):
        try:
            # Search for part information using one of the following:
            #    1) the distributor's catalog number.
            #    2) the manufacturer's part number.
            for key in (dist+'#', dist+SEPRTR+'cat#', 'manf#'):
                if key in part.fields:
                    if part.fields[key]:
                        # Founded manufacturer / distributor code valid (not empty).
                        return get_html_tree_func(dist, part.fields[key], extra_search_terms, local_part_html=local_part_html, scrape_retries=scrape_retries)
            # No distributor or manufacturer number, so give up.
            else:
                logger.warning("No '%s#' or 'manf#' field: cannot lookup part %s at %s", dist, part.refs, dist)
                return BeautifulSoup('<html></html>', 'lxml'), ''
                #raise PartHtmlError
        except PartHtmlError:
            pass
        except AttributeError:
            break
    logger.warning("Part %s not found at %s", part.refs, dist)
    # If no HTML page was found, then return a tree for an empty page.
    return BeautifulSoup('<html></html>', 'lxml'), ''


def scrape_part(args):
    '''Scrape the data for a part from each distributor website or local HTML.'''

    id, part, distributor_dict, local_part_html, scrape_retries, log_level = args # Unpack the arguments.

    if multiprocessing.current_process().name == "MainProcess":
        scrape_logger = logging.getLogger('kicost')
    else:
        scrape_logger = multiprocessing.get_logger()
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        scrape_logger.addHandler(handler)
        scrape_logger.setLevel(log_level)

    # Create dictionaries for the various items of part data from each distributor.
    url = {}
    part_num = {}
    price_tiers = {}
    qty_avail = {}

    # Scrape the part data from each distributor website or the local HTML.
    for d in distributor_dict:
        try:
            dist_module = getattr(distributor_imports, d)
        except AttributeError:
            dist_module = getattr(distributor_imports, distributor_dict[d]['module'])

        # Get the HTML tree for the part.
        html_tree, url[d] = get_part_html_tree(part, d, dist_module.get_part_html_tree, local_part_html, scrape_retries, scrape_logger)

        # Call the functions that extract the data from the HTML tree.
        part_num[d] = dist_module.get_part_num(html_tree)
        qty_avail[d] = dist_module.get_qty_avail(html_tree)
        price_tiers[d] = dist_module.get_price_tiers(html_tree)

    # Return the part data.
    return id, url, part_num, price_tiers, qty_avail
