# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Max Maisel / Hildo Guillardi Júnior
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
import json
import requests
import re
import os
import sys
from collections import Counter
if sys.version_info[0] < 3:
    from urllib import quote_plus
else:
    from urllib.parse import quote_plus

# KiCost definitions.
from ..global_vars import DEBUG_OVERVIEW, DEBUG_OBSESSIVE, ERR_SCRAPE, KiCostError, W_ASSQTY
# Distributors definitions.
from .distributor import distributor_class

# Author information.
__author__ = 'XESS Corporation'
__webpage__ = 'info@xess.com'

# SET: The following isn't need in all KiCost, I don't think is really needed here.
#      If you think this is needed contact me, we can use the same tricks used in the rest of the code.
# Python2/3 compatibility.
# from future import standard_library
# standard_library.install_aliases()

OCTOPART_MAX_PARTBYQUERY = 20  # Maximum part list length to one single query.

__all__ = ['api_octopart']


class api_octopart(distributor_class):
    name = 'Octopart'
    type = 'api'
    enabled = False
    url = 'https://octopart.com/'  # Web site API information.
    api_level = 4
    # Include specs and datasheets. Only in the Pro plan.
    extended = False

    API_KEY = None
    API_DISTRIBUTORS = ['arrow', 'digikey', 'farnell', 'mouser', 'newark', 'rs', 'tme']
    DIST_TRANSLATION = {  # Distributor translation.
                        'arrow': 'Arrow Electronics, Inc.',
                        'digikey': 'Digi-Key',
                        'farnel': 'Farnell',
                        'mouser': 'Mouser',
                        'newark': 'Newark',
                        'rs': 'RS Components',
                        'tme': 'TME',
                        'lcsc': 'LCSC',
                       }

    @staticmethod
    def init_dist_dict():
        if api_octopart.enabled:
            distributor_class.add_distributors(api_octopart.API_DISTRIBUTORS)

    @staticmethod
    def set_options(key, level):
        if key:
            if key.lower() == 'none':
                api_octopart.enabled = False
            else:
                api_octopart.API_KEY = key
                api_octopart.enabled = True
        if level:
            if level[-1] == 'p':
                api_octopart.extended = True
                level = level[:-1]
            else:
                api_octopart.extended = False
            api_octopart.api_level = int(level)
        distributor_class.logger.log(DEBUG_OBSESSIVE, 'Octopart API configured to enabled {} key {} level {} extended {}'.
                                     format(api_octopart.enabled, api_octopart.API_KEY, api_octopart.api_level, api_octopart.extended))

    def query(query):
        """Send query to Octopart and return results."""
        # url = 'http://octopart.com/api/v3/parts/match'
        # payload = {'queries': json.dumps(query), 'include\[\]': 'specs', 'apikey': token}
        # response = requests.get(url, params=payload)
        data = 'queries=%s' % json.dumps(query)
        if api_octopart.API_KEY:
            if api_octopart.api_level == 3:
                url = 'http://octopart.com/api/v3/parts/match'
            else:
                url = 'http://octopart.com/api/v4/rest/parts/match'
            data += '&apikey=' + api_octopart.API_KEY
        else:  # Not working 2021/04/28:
            url = 'https://temp-octopart-proxy.kitspace.org/parts/match'
        # Allow changing the URL for debug purposes
        try:
            url = os.environ['KICOST_OCTOPART_URL']
        except KeyError:
            pass
        if api_octopart.extended:
            data += '&include[]=specs'
            data += '&include[]=datasheets'
        distributor_class.log_request(url, data)
        response = requests.get(url + '?' + data)
        distributor_class.log_response(response)
        if response.status_code == 200:  # Ok
            results = json.loads(response.text).get('results')
            return results
        elif response.status_code == 400:  # Bad request
            raise KiCostError('Octopart missing apikey.', ERR_SCRAPE)
        elif response.status_code == 404:  # Not found
            raise KiCostError('Octopart server not found.', ERR_SCRAPE)
        elif response.status_code == 403 or 'Invalid API key' in response.text:
            raise KiCostError('Octopart KEY invalid, register one at "https://www.octopart.com".', ERR_SCRAPE)
        elif response.status_code == 429:  # Too many requests
            raise KiCostError('Octopart request limit reached.', ERR_SCRAPE)
        else:
            raise KiCostError('Octopart error: ' + str(response.status_code), ERR_SCRAPE)

    def sku_to_mpn(sku):
        """Find manufacturer part number associated with a distributor SKU."""
        part_query = [{'reference': '1', 'sku': quote_plus(sku)}]
        results = api_octopart.query(part_query)
        if not results:
            return None
        result = results[0]
        mpns = [item['mpn'] for item in result['items']]
        if not mpns:
            return None
        if len(mpns) == 1:
            return mpns[0]
        mpn_cnts = Counter(mpns)
        return mpn_cnts.most_common(1)[0][0]  # Return the most common MPN.

    def skus_to_mpns(parts, distributors):
        """Find manufaturer's part number for all parts with just distributor SKUs."""
        for i, part in enumerate(parts):

            # Skip parts that already have a manufacturer's part number.
            if part.fields.get('manf#'):
                continue

            # Get all the SKUs for this part.
            skus = list(
                set([part.fields.get(dist + '#', '') for dist in distributors]))
            skus = [sku for sku in skus
                    if sku not in ('', None)]  # Remove null SKUs.

            # Skip this part if there are no SKUs.
            if not skus:
                continue

            # Convert the SKUs to manf. part numbers.
            mpns = [api_octopart.sku_to_mpn(sku) for sku in skus]
            mpns = [mpn for mpn in mpns
                    if mpn not in ('', None)]  # Remove null manf#.

            # Skip assigning manf. part number to this part if there aren't any to assign.
            if not mpns:
                continue

            # Assign the most common manf. part number to this part.
            mpn_cnts = Counter(mpns)
            part.fields['manf#'] = mpn_cnts.most_common(1)[0][0]

    def query_part_info(parts, distributors, currency):
        """Fill-in the parts with price/qty/etc info from Octopart."""
        distributor_class.logger.log(DEBUG_OVERVIEW, '# Getting part data from Octopart...')

        # Setup progress bar to track progress of Octopart queries.
        progress = distributor_class.progress(len(parts), distributor_class.logger)

        # Translate from Octopart distributor names to the names used internally by kicost.
        dist_xlate = api_octopart.DIST_TRANSLATION

        def get_part_info(query, parts, currency='USD'):
            """Query Octopart for quantity/price info and place it into the parts list."""

            results = api_octopart.query(query)

            # Loop through the response to the query and enter info into the parts list.
            for result in results:
                i = int(result['reference'])  # Get the index into the part dict.
                part = parts[i]
                # Loop through the offers from various dists for this particular part.
                for item in result['items']:

                    # Assign the lifecycle status 'obsolete' (others possible: 'active'
                    # and 'not recommended for new designs') but not used.
                    specs = item.get('specs')
                    if specs:
                        lifecycle_status = specs.get('lifecycle_status')
                        if lifecycle_status:
                            lifecycle_status = lifecycle_status['value'][0].lower()
                            if lifecycle_status == 'obsolete':
                                part.lifecycle = lifecycle_status
                    # Take the datasheet provided by the distributor. This will by used
                    # in the output spreadsheet if not provide any in the BOM/schematic.
                    # This will be signed in the file.
                    datasheets = item.get('datasheets')
                    if datasheets:
                        part.datasheet = datasheets[0]['url']

                    for offer in item['offers']:

                        # Get the distributor who made the offer and add their
                        # price/qty info to the parts list if its one of the accepted distributors.
                        dist = dist_xlate.get(offer['seller']['name'], '')
                        if dist in distributors:

                            # Get pricing information from this distributor.
                            try:
                                price_tiers = {}  # Empty dict in case of exception.
                                dist_currency = list(offer['prices'].keys())
                                parts.currency[dist] = dist_currency[0]
                                price_tiers = {qty: float(price) for qty, price in list(offer['prices'].values())[0]}
                                # Combine price lists for multiple offers from the same distributor
                                # to build a complete list of cut-tape and reeled components.
                                if dist not in part.price_tiers:
                                    part.price_tiers[dist] = {}
                                part.price_tiers[dist].update(price_tiers)
                            except Exception:
                                pass  # Price list is probably missing so leave empty default dict in place.

                            # Compute the quantity increment between the lowest two prices.
                            # This will be used to distinguish the cut-tape from the reeled components.
                            try:
                                part_break_qtys = sorted(price_tiers.keys())
                                part_qty_increment = part_break_qtys[1] - part_break_qtys[0]
                            except Exception:
                                # This will happen if there are not enough entries in the price/qty list.
                                # As a stop-gap measure, just assign infinity to the part increment.
                                # A better alternative may be to examine the packaging field of the offer.
                                part_qty_increment = float("inf")

                            # Select the part SKU, web page, and available quantity.
                            # Each distributor can have different stock codes for the same part in different
                            # quantities / delivery package styles: cut-tape, reel, ...
                            # Therefore we select and overwrite a previous selection if one of the
                            # following conditions is met:
                            #   1. We don't have a selection for this part from this distributor yet.
                            #   2. The MOQ is smaller than for the current selection.
                            #   3. The part_qty_increment for this offer smaller than that of the existing selection.
                            #      (we prefer cut-tape style packaging over reels)
                            #   4. For DigiKey, we can't use part_qty_increment to distinguish between
                            #      reel and cut-tape, so we need to look at the actual DigiKey part number.
                            #      This procedure is made by the definition `distributors_info[dist]['ignore_cat#_re']`
                            #      at the distributor profile.
                            if not part.part_num.get(dist):
                                qty_avail = part.qty_avail.get(dist)
                                if not qty_avail or (offer.get('in_stock_quantity') and qty_avail < offer.get('in_stock_quantity')):
                                    # Keeps the information of more availability.
                                    part.qty_avail[dist] = offer.get('in_stock_quantity')
                                moq = part.moq.get(dist)
                                if not moq or (offer.get('moq') and moq > offer.get('moq')):
                                    # Save the link, stock code, ... of the page for minimum purchase.
                                    part.moq[dist] = offer.get('moq')  # Minimum order qty.
                                    part.part_num[dist] = offer.get('sku')
                                    part.url[dist] = offer.get('product_url')
                                    part.qty_increment[dist] = part_qty_increment
                            # Otherwise, check qty increment and see if its the smallest for this part & dist.
                            elif part_qty_increment < part.qty_increment.get(dist):
                                # This part looks more like a cut-tape version, so
                                # update the SKU, web page, and available quantity.
                                qty_avail = part.qty_avail.get(dist)
                                if not qty_avail or (offer.get('in_stock_quantity') and qty_avail < offer.get('in_stock_quantity')):
                                    # Keeps the information of more availability.
                                    part.qty_avail[dist] = offer.get('in_stock_quantity')
                                ign_stock_code = distributor_class.get_distributor_info(dist).ignore_cat
                                # TODO dist_part_num wan't defined, I copied it from KitSpace API
                                dist_part_num = offer.get('sku', '').get('part', '')
                                valid_part = not (ign_stock_code and re.match(ign_stock_code, dist_part_num))
                                if valid_part and \
                                    (not part.part_num.get(dist) or
                                     (part_qty_increment < part.qty_increment.get(dist)) or
                                     (not part.moq.get(dist) or (offer.get('moq') and part.moq.get(dist) > offer.get('moq')))):
                                    # Save the link, stock code, ... of the page for minimum purchase.
                                    part.moq[dist] = offer.get('moq')  # Minimum order qty.
                                    part.part_num[dist] = offer.get('sku')
                                    part.url[dist] = offer.get('product_url')
                                    part.qty_increment[dist] = part_qty_increment

                            # Don't bother with any extra info from the distributor.
                            part.info_dist[dist] = {}

        # Get the valid distributors names used by them part catalog
        # that may be index by Octopart. This is used to remove the
        # local distributors and future not implemented in the Octopart
        # definition.
        # Note: The user can use --exclude and define it with fields.
        distributors_octopart = [d for d in distributors if distributor_class.get_distributor_info(d).is_web()
                                 and d in api_octopart.API_DISTRIBUTORS]

        # Break list of parts into smaller pieces and get price/quantities from Octopart.
        octopart_query = []
        prev_i = 0  # Used to record index where parts query occurs.
        for i, part in enumerate(parts):

            # Create an Octopart query using the manufacturer's part number or
            # distributor SKU.
            manf_code = part.fields.get('manf#')
            if manf_code:
                part_query = {'reference': str(i), 'mpn': quote_plus(manf_code)}
            else:
                try:
                    # No MPN, so use the first distributor SKU that's found.
                    # skus = [part.fields.get(d + '#', '') for d in distributors_octopart
                    #            if part.fields.get(d + '#') ]
                    for octopart_dist_sku in distributors_octopart:
                        sku = part.fields.get(octopart_dist_sku + '#', '')
                        if sku:
                            break
                    if not sku:
                        continue
                    # Create the part query using SKU matching.
                    part_query = {'reference': str(i), 'sku': quote_plus(sku)}

                    # Because was used the distributor (enrolled at Octopart list)
                    # despite the normal 'manf#' code, take the sub quantity as
                    # general sub quantity of the current part.
                    try:
                        part.fields['manf#_qty'] = part.fields[octopart_dist_sku + '#_qty']
                        distributor_class.logger.warning(W_ASSQTY+"Associated {q} quantity to '{r}' due \"{f}#={q}:{c}\".".format(
                                q=part.fields[octopart_dist_sku + '#_qty'], r=part.refs,
                                f=octopart_dist_sku, c=part.fields[octopart_dist_sku+'#']))
                    except KeyError:
                        pass
                except IndexError:
                    # No MPN or SKU, so skip this part.
                    continue

            # Add query for this part to the list of part queries.
            octopart_query.append(part_query)

            # Once there are enough (but not too many) part queries, make a query request to Octopart.
            if len(octopart_query) == OCTOPART_MAX_PARTBYQUERY:
                get_part_info(octopart_query, parts)
                progress.update(i - prev_i)  # Update progress bar.
                prev_i = i
                octopart_query = []  # Get ready for next batch.

        # Query Octopart for the last batch of parts.
        if octopart_query:
            get_part_info(octopart_query, parts)
            progress.update(len(parts)-prev_i)  # This will indicate final progress of 100%.

        # Done with the scraping progress bar so delete it or else we get an
        # error when the program terminates.
        progress.close()


# Configure the module from the environment
# The command line will overwrite it using set_options()
key = os.environ.get('KICOST_OCTOPART_KEY_V3')
if key:
    api_octopart.API_KEY = key
    api_octopart.enabled = True
    api_octopart.api_level = 3
else:
    key = os.environ.get('KICOST_OCTOPART_KEY_V4')
    if key:
        api_octopart.API_KEY = key
        api_octopart.enabled = True
        api_octopart.api_level = 4
    elif os.environ.get('KICOST_OCTOPART'):
        # Currently this isn't useful, you can't do anything without a key.
        # This is just in case we get a proxy running.
        api_octopart.enabled = True
if os.environ.get('KICOST_OCTOPART_EXTENDED'):
    api_octopart.extended = True
distributor_class.register(api_octopart, 60)
