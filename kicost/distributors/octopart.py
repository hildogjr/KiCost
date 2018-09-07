# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Max Maisel
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
__author__ = 'XESS Corporation'
__webpage__ = 'info@xess.com'

# Libraries.
import json
import requests
import logging
import tqdm
import copy
import re

from ..global_vars import logger, DEBUG_OVERVIEW, DEBUG_OBSESSIVE # Debug configurations.
from ..global_vars import SEPRTR


def handle_local_parts(parts, distributors):
    """Fill-in part information for locally-sourced parts not handled by Octopart."""

    # This loops through all the parts and finds any that are sourced from 
    # local distributors that are not normally searched and places them into 
    # the distributor disctionary.
    for part in parts:
        # Find the various distributors for this part by
        # looking for leading fields terminated by SEPRTR.
        for key in part.fields:
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

    # Set part info to default values for all the distributors.
    for part in parts:
        part.part_num = {dist:'' for dist in distributors}
        part.url = {dist:'' for dist in distributors}
        part.price_tiers = {dist:{} for dist in distributors}
        part.qty_avail = {dist:None for dist in distributors}
        part.qty_increment = {dist:None for dist in distributors}
        part.info_dist = {dist:{} for dist in distributors}

    # Loop through the parts looking for those sourced by local distributors
    # that won't be found online. Place any user-added info for these parts
    # (such as pricing) into the part dictionary.
    for p in parts:
        # Find the manufacturer's part number if it exists.
        pn = p.fields.get('manf#') # Returns None if no manf# field.

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
            p.part_num[dist] = cat_num

            link = ''
            try:
                url_parts = list(urlsplit(link))
                if url_parts[0] == '':
                    url_parts[0] = u'http'
                link = urlunsplit(url_parts)
            except Exception:
                # This happens when no part URL is found.
                logger.log(DEBUG_OBSESSIVE, 'No local part URL found!')
            p.url[dist] = link
                
            price_tiers = {}
            try:
                pricing = re.sub('[^0-9.;:]', '', pricing) # Keep only digits, decimals, delimiters.
                for qty_price in pricing.split(';'):
                    qty, price = qty_price.split(SEPRTR)
                    price_tiers[int(qty)] = float(price)
            except AttributeError:
                # This happens when no pricing info is found.
                logger.log(DEBUG_OBSESSIVE, 'No local pricing information found!')
            p.price_tiers[dist] = price_tiers

    # Remove the local distributor template so it won't be processed later on.
    # It has served its purpose.
    try:
        del distributors['local_template']
    except:
        pass


def query_octopart(parts, distributors):
    """Fill-in the parts with price/qty/etc info from Octopart."""

    # Fill-in info for any locally-sourced parts not handled by Octopart.
    handle_local_parts(parts, distributors)

    logger.log(DEBUG_OVERVIEW, '# Getting part data from Octopart...')

    # Setup progress bar to track progress of Octopart queries.
    progress = tqdm.tqdm(desc='Progress', total=len(parts), unit='part', miniters=1)

    # Change the logging print channel to `tqdm` to keep the process bar to the end of terminal.
    class TqdmLoggingHandler(logging.Handler):
        '''Overload the class to write the logging through the `tqdm`.'''
        def __init__(self, level = logging.NOTSET):
            super(self.__class__, self).__init__(level)
        def emit(self, record):
            try:
                msg = self.format(record)
                tqdm.tqdm.write(msg)
                self.flush()
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                self.handleError(record)
            pass

    # Get handles to default sys.stdout logging handler and the
    # new "tqdm" logging handler.
    logDefaultHandler = logger.handlers[0]
    logTqdmHandler = TqdmLoggingHandler()

    # Replace default handler with "tqdm" handler.
    logger.addHandler(logTqdmHandler)
    logger.removeHandler(logDefaultHandler)

    # Translate from Octopart distributor names to the names used internally by kicost.
    dist_xlate = {dist_value['octopart_name']:dist_key for dist_key, dist_value in distributors.items()}

    def get_part_info(query, parts):
        """Query Octopart for quantity/price info and place it into the parts list."""

        # Create query URL for Octopart.
        url = 'http://octopart.com/api/v3/parts/match'
        payload = {'queries':json.dumps(query), 'apikey':'96df69ba'}
        response = requests.get(url, params=payload)
        results = json.loads(response.text)['results']

        # Loop through the response to the query and enter part info into the parts list.
        for result in results:
            i = int(result['reference']) # Get the index into the part dictionary.

            # Loop through the offers from various distributors for this particular part.
            for item in result['items']:
                for offer in item['offers']:

                    # Get the distributor who made the offer and add their 
                    # price/qty info to the parts list if its one of the accepted distributors.
                    dist = dist_xlate.get(offer['seller']['name'], '')
                    if dist in distributors:

                        # Get pricing information from this distributor.
                        try:
                            price_tiers = {} # Empty dict in case of exception.
                            price_tiers = {qty:float(price) for qty, price in list(offer['prices'].values())[0]}
                            # Combine price lists for multiple offers from the same distributor
                            # to build a complete list of cut-tape and reeled components.
                            parts[i].price_tiers[dist].update(price_tiers)
                        except Exception:
                            pass  # Price list is probably missing so leave empty default dict in place.

                        # Compute the quantity increment between the lowest two prices.
                        # This will be used to distinguish the cut-tape from the reeled components.
                        try:
                            part_break_qtys = sorted(price_tiers.keys())
                            part_qty_increment = part_break_qtys[1] - part_break_qtys[0]
                        except Exception:
                            pass

                        # Use the qty increment to select the part SKU, web page, and available quantity.
                        # Do this if this is the first part offer from this dist.
                        if not parts[i].part_num[dist]:
                            parts[i].part_num[dist] = offer.get('sku', '')
                            parts[i].url[dist] = offer.get('product_url', '')
                            parts[i].qty_avail[dist] = offer.get('in_stock_quantity', None)
                            parts[i].qty_increment[dist] = part_qty_increment
                        # Otherwise, check qty increment and see if its the smallest for this part & dist.
                        elif part_qty_increment < parts[i].qty_increment[dist]:
                                # This part looks more like a cut-tape version, so
                                # update the SKU, web page, and available quantity.
                                parts[i].part_num[dist] = offer.get('sku', '')
                                parts[i].url[dist] = offer.get('product_url', '')
                                parts[i].qty_avail[dist] = offer.get('in_stock_quantity', None)
                                parts[i].qty_increment[dist] = part_qty_increment

                        # Don't bother with any extra info from the distributor.
                        parts[i].info_dist[dist] = {}

    # Break list of parts into smaller pieces and get price/quantities from Octopart.
    octopart_query = []
    for i, part in enumerate(parts):

        # Get manufacturer's part number for doing Octopart search.
        try:
            mpn = part.fields['manf#']
        except KeyError:
            continue # No manf. part number, so don't add this part to the query.

        # Add query for this part to the list of part queries.
        part_query = dict([('reference', i), ('mpn', mpn)])
        octopart_query.append(part_query)

        # Once there are enough (but not too many) part queries, make a query request to Octopart.
        if len(octopart_query) == 20:
            get_part_info(octopart_query, parts)
            progress.update(len(octopart_query))
            octopart_query = [] # Clear list of queries to get ready for next batch.

    # Query Octopart for the last batch of parts.
    if octopart_query:
        get_part_info(octopart_query, parts)
        progress.update(len(octopart_query))

    # Restore the logging print channel now that the progress bar is no longer needed.
    logger.addHandler(logDefaultHandler)
    logger.removeHandler(logTqdmHandler)

    # Done with the scraping progress bar so delete it or else we get an 
    # error when the program terminates.
    del progress

