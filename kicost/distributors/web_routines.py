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

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# Libraries.
import sys
from bs4 import BeautifulSoup # XML file interpreter.
from yattag import Doc, indent  # For generating HTML page for local parts.
import multiprocessing # To deal with the parallel scrape.
import logging
from ..kicost import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE # Debug configurations.
from ..kicost import SEPRTR
#from . import distributors

__all__ = ['scrape_part', 'get_part_html_tree', 'create_local_part_html']

# Extra informations to by got by each part in the distributors.
EXTRA_INFO = ['value', 'tolerance', 'footprint', 'power', 'current', 'voltage', 'frequency', 'temp_coeff', 'manf',
              'datasheet', 'image' # Links.
             ]

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
    print(__all__) #TODO ERROR
    print(dir(locals()) #TODO ERROR
    for d in distributor_dict:
        try:
            #dist_module = getattr(distributor_imports, d)
            dist_module = getattr(locals(), d)
        except AttributeError:
            #dist_module = getattr(distributor_imports, distributor_dict[d]['module'])
            dist_module = getattr(locals(), distributor_dict[d]['module'])

        # Get the HTML tree for the part.
        html_tree, url[d] = get_part_html_tree(part, d, dist_module.get_part_html_tree, local_part_html, scrape_retries, scrape_logger)

        # Call the functions that extract the data from the HTML tree.
        part_num[d] = dist_module.get_part_num(html_tree)
        qty_avail[d] = dist_module.get_qty_avail(html_tree)
        price_tiers[d] = dist_module.get_price_tiers(html_tree)

    # Return the part data.
    return id, url, part_num, price_tiers, qty_avail