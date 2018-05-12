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
import multiprocessing # To deal with the parallel scrape.
import logging
from time import time
from random import choice
from ..eda_tools.eda_tools import order_refs # To better print the warnings about the parts.

try:
    # This is for Python 3.
    from urllib.parse import urlsplit, urlunsplit
except ImportError:
    # This is for Python 2.
    from urlparse import urlsplit, urlunsplit

from ..globals import logger, DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE # Debug configurations.
from ..globals import SEPRTR
from ..globals import PartHtmlError
from . import distributor_dict

import os, re

# The distributor module directories will be found in this directory.
directory = os.path.dirname(__file__)

# Search for the distributor modules and import them.
dist_modules = {}
for module in os.listdir(directory):

    # Avoid importing non-directories.
    abs_module = os.path.join(directory, module)
    if not os.path.isdir(abs_module):
        continue

    # Avoid directories like __pycache__.
    if module.startswith('__'):
        continue

    # Import the module.
    dist_modules[module] = __import__(module, globals(), locals(), [], level=1)

__all__ = ['scrape_part', 'config_distributor']

def config_distributor(dist_name, locale_currency='USD'):
    '''@brief Configure the distributor for some locale/country and
    currency second ISO3166 and ISO4217
    
    @param `str` dist Distributor to configure.
    @param `str` Alpha 2 country or alpha 3 currency or even one slash other.'''
    try:
        dist_module = dist_modules[dist_name]
    except KeyError: # When use local distributor with personalized name.
        dist_module = dist_modules[distributor_dict[dist_name]['module']]
    try:
        if distributor_dict[dist_name]['scrape']=='web':
            # Not make sense to configurate a local distributor (yet).
            locale_currency = re.findall('\w{2,}', locale_currency)
            locale = None
            currency = None
            for alpha in locale_currency:
                if len(alpha)==2:
                    locale = alpha
                elif len(alpha)==3:
                    currency = alpha
            dist_module.define_locale_currency(locale_iso=locale, currency_iso=currency)
    except AttributeError:
        logger.warning('No currency/country configuration for {}.'.format(distributor_dict[dist_name]['label']))
        pass


def get_part_html_tree(part, dist, get_html_tree_func, local_part_html, scrape_retries, logger):
    '''@brief Get the HTML tree for a part.
    
    Get the HTML tree for a part from the given distributor website or local HTML.
    @param `str` part Part manufactor code or distributor stock code.
    @param `str` dist Distributor do scrape.
    @param `str` get_html_tree_func
    @param `str` local_part_html
    @param `int` scrape_retries Maximum times of web ritries.
    @param logger Logger handle.
    @return `str` with the HTML webpage.'''

    logger.log(DEBUG_OBSESSIVE, 'Looking in %s by %s:', distributor_dict[dist]['label'], order_refs(part.refs, True))

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
                logger.warning("No '%s#' or 'manf#' field: cannot lookup part %s at %s.", dist, part.refs, dist)
                return BeautifulSoup('<html></html>', 'lxml'), ''
                #raise PartHtmlError
        except PartHtmlError:
            pass
        except AttributeError:
            break
    logger.warning("Part %s not found at %s.", order_refs(part.refs, False), distributor_dict[dist]['label'])
    # If no HTML page was found, then return a tree for an empty page.
    return BeautifulSoup('<html></html>', 'lxml'), ''


def scrape_part(args):
    '''@brief Scrape the data for a part from each distributor website or local HTML.
    
    Use distributors submodules to scrape each distributor part page and get
    informations such as price, quantity avaliable and others;
    
    @param `int` Count of the main loop.
    @param `str`String with the part number / distributor stock.
    @param `dict`
    @param `str`
    @param `int`Number of scrape retries.
    @param logger.getEffectiveLevel()
    @param throttle_lock
    @param throttle_tim
    @return id, url, `str` distributor stock part number, `dict` price tiers, `int` qty avail, `dict` extrainfo dist
    '''

    id, part, distributor_dict, local_part_html, scrape_retries, log_level, throttle_lock, throttle_timeouts = args # Unpack the arguments.

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
    info_dist = {}

    # Scrape the part data from each distributor website or the local HTML.
    # Create a list of the distributor keys and randomly choose one of the
    # keys to scrape. After scraping, remove the distributor key.
    # Do this until all the distributors have been scraped.
    distributors = list(distributor_dict.keys())
    while distributors:

        d = choice(distributors)  # Randomly choose one of the available distributors.

        try:
            #dist_module = getattr(THIS_MODULE, d)
            dist_module = dist_modules[d]
        except KeyError: # When use local distributor with personalized name.
            dist_module = dist_modules[distributor_dict[d]['module']]

        # Try to access the list of distributor throttling timeouts.
        # Abort if some other process is already using the timeouts.
        if throttle_lock.acquire(blocking=False):

            # Check the throttling timeout for the chosen distributor to see if
            # another access to its website is allowed.
            if throttle_timeouts[d] <= time():

                # Update the timeout for this distributor website and release the sync. lock.
                throttle_timeouts[d] = time() + distributor_dict[d]['throttling_delay']
                throttle_lock.release()

                # Get the HTML tree for the part.
                html_tree, url[d] = get_part_html_tree(part, d, dist_module.get_part_html_tree, local_part_html, scrape_retries, scrape_logger)

                # Call the functions that extract the data from the HTML tree.
                part_num[d] = dist_module.get_part_num(html_tree)
                qty_avail[d] = dist_module.get_qty_avail(html_tree)
                price_tiers[d] = dist_module.get_price_tiers(html_tree)
                
                try:
                    # Get extra characeristics of the part in the web page.
                    # This will be use to comment in the 'cat#' column of the
                    # spreadsheet and some validations (in the future implementaions)
                    info_dist[d] = dist_module.get_extra_info(html_tree)
                except:
                    info_dist[d] = {}
                    pass

                # The part data has been scraped from this distributor, so remove it from the list.
                distributors.remove(d)

            # If the timeout for this distributor has not expired, then release
            # the sync. lock and try another distributor.
            else:
                throttle_lock.release()

    # Return the part data.
    return id, url, part_num, price_tiers, qty_avail, info_dist
