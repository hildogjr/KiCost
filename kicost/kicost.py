# MIT license
# 
# Copyright (C) 2015 by XESS Corporation
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

import pprint
import bs4 as BS
import difflib
import xml.etree.ElementTree as ET
import urllib as URLL

DELIMITER = ':'

# Global array of distributor names.
distis = ['digikey', 'mouser']


def kicost(infile, qty, outfile):

    # Read-in the schematic XML file to get a tree and get its root.
    tree = ET.parse(infile)
    root = tree.getroot()

    # Find the parts used from each library.
    libparts = {}
    for p in root.find('libparts').iter('libpart'):

        # Get the values for the fields in each part (if any).
        fields = {}  # Clear the field dict for this part.
        try:
            for f in p.find('fields').iter('field'):
                # Store the name and value for each field.
                fields[f.get('name').lower()] = f.text
        except AttributeError:
            # No fields found for this part.
            pass

        # Store the field dict under the key made from the
        # concatenation of the library and part names.
        libparts[p.get('lib') + DELIMITER + p.get('part')] = fields

    # Find the components used in the schematic and elaborate
    # them with global values from the libraries and local values
    # from the schematic.
    components = {}
    for c in root.find('components').iter('comp'):

        # Find the library used for this component.
        libsource = c.find('libsource')

        # Create the key to look up the part in the libparts dict.
        libpart = libsource.get('lib') + DELIMITER + libsource.get('part')

        # Initialize the fields from the global values in the libparts dict entry.
        # (These will get overwritten by any local values down below.)
        fields = libparts[libpart].copy()  # Make a copy! Don't use reference!

        # Store the part key and its value.
        fields['libpart'] = libpart
        fields['value'] = c.find('value').text

        # Get the footprint for the part (if any) from the schematic.
        try:
            fields['footprint'] = c.find('footprint').text
        except AttributeError:
            pass

        # Get the values for any other the fields in the part (if any) from the schematic.
        try:
            for f in c.find('fields').iter('field'):
                fields[f.get('name').lower()] = f.text
        except AttributeError:
            pass

        # Store the fields for the part using the reference identifier as the key.
        ref = c.get('ref')
        components[c.get('ref')] = fields

    # Get groups of identical components.
    component_groups = {}
    for c in components:

        # Take the field keys and values of each part and create a hash.
        # Use the hash as the key to a dictionary that stores lists of
        # part references that have identical field values.
        h = hash(tuple(sorted(components[c].items())))

        # Now add the hashed component to the group with the matching hash
        # or create a new group if the hash hasn't been seen before.
        try:
            # Add next ref for indentical part to the list.
            # No need to add field values since they are the same as the 
            # starting ref field values.
            component_groups[h].refs.append(c)
        except KeyError:

            class IdenticalComponents:
                pass  # Just need a temporary class here.

            component_groups[h] = IdenticalComponents()  # Add empty structure.
            component_groups[h].refs = [c]  # Init list of refs with first ref.
            component_groups[h].fields = components[c]  # Store field values.

    # Calculate the quantity needed of each part.
    for part in component_groups.values():
        # part quantity = qty of boards * # of identical components per board.
        part.qty = qty * len(part.refs)

    # Get the parsed product pages for each part from each distributor.
    for part in component_groups.values():
        part.html_trees = get_part_html_trees(part)

    # Lookup the price tiers of each component for each distributor.
    for part in component_groups.values():
        part.price_tiers = get_price_tiers(part.html_trees)

    # Get total cost of each component from each distributor.
    for part in component_groups.values():
        part.total_costs = get_costs(part.qty, part.price_tiers)

    # Get the total price of the board for each distributor.
    board_cost = {}
    for dist in distis:
        board_cost[dist] = 0.0
        for part in component_groups.values():
            try:
                board_cost[dist] += part.total_costs[dist]
            except TypeError:
                pass
        print '{} cost = {:.2f}'.format(dist, board_cost[dist])

    # Print component groups for debugging purposes.
    for part in component_groups.values():
        for f in dir(part):
            if f.startswith('__'):
                continue
            elif f.startswith('html_trees'):
                continue
            else:
                print '{} = '.format(f),
                pprint.pprint(part.__dict__[f])
        print


def get_costs(qty, price_tiers):
    '''Get the total cost for a part used in a schematic.'''

    def qty_cost(qty, tiers):
        '''Get the unit cost of a part at a particular quantity.'''
        cost = tiers[0].unit_price # Start off at lowest quantity price.
        
        # Go through tiers of increasing quantity.
        for t in tiers:

            # Exit loop when the requested quantity doesn't qualify for this tier.
            if qty < t.qty:
                break

            # Otherwise, set unit price to be this tier price and keep on looking.
            cost = t.unit_price
            
        # Return the unit cost for the highest qualifying tier.
        return cost

    costs = {}
    for dist in distis:
        try:
            costs[dist] = qty * qty_cost(qty, price_tiers[dist])
        except IndexError:
            # This happens when the part isn't offered by this distributor.
            costs[dist] = '???'
    return costs


def get_price_tiers(html_trees):
    '''Get the pricing tiers from the parsed trees of distributor product pages.'''
    price_tiers = {}
    for dist in distis:
        price_tiers[dist] = eval(
            'get_' + dist + '_price_tiers(html_trees[dist])')
    return price_tiers


class QtyPrice:
    '''Class for holding price and quantity for a pricing tier.'''
    def __repr__(self):
        return 'Qty: ' + str(self.qty) + '  Price: ' + str(self.unit_price)

    def __str__(self):
        return 'Qty: ' + str(self.qty) + '  Price: ' + str(self.unit_price)


def get_digikey_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Digikey product page.'''
    price_tiers = []
    try:
        for tr in html_tree.find(id='pricing').find_all('tr'):
            try:
                td = tr.find_all('td')
                if len(td) == 2:
                    qty_price = QtyPrice()
                    qty_price.qty = int(td[0].text)
                    qty_price.unit_price = float(td[1].text)
                    price_tiers.append(qty_price)
                elif len(td) == 3:
                    qty_price = QtyPrice()
                    qty_price.qty = int(td[0].text)
                    qty_price.unit_price = min(float(td[1].text),
                                               float(td[2].text))
                    price_tiers.append(qty_price)
                else:
                    continue
            except TypeError:  # Happens when there's no <td> in table row.
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        pass
    return price_tiers


def get_mouser_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Mouser product page.'''
    price_tiers = []
    try:
        for tr in html_tree.find('table', class_='PriceBreaks').find_all('tr'):
            try:
                qty_price = QtyPrice()
                qty_price.qty = int(
                    tr.find('td',
                            class_='PriceBreakQuantity').a.text)
                qty_price.unit_price = float(
                    tr.find('td',
                            class_='PriceBreakPrice').text[2:])
                price_tiers.append(qty_price)
            except TypeError:  # Happens when there's no <td> in table row.
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        pass
    return price_tiers


def get_part_html_trees(part):
    '''Get the parsed HTML trees from each distributor website for the given part.'''
    html_trees = {}
    fields = part.fields
    for dist in distis:
        try:
            if dist + '#' in fields:
                html_trees[dist] = eval(
                    'get_' + dist + '_part_html_tree(fields[dist+"#"])')
            elif 'manf#' in fields:
                html_trees[dist] = eval(
                    'get_' + dist + '_part_html_tree(fields["manf#"])')
            else:
                raise PartHtmlError
        except PartHtmlError, AttributeError:
            html_trees[dist] = BS.BeautifulSoup('<html></html>')
    return html_trees


class FakeBrowser(URLL.FancyURLopener):
    ''' This is a fake browser string so the distributor websites will talk to us.'''
    version = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.124 Safari/537.36'


class PartHtmlError(Exception):
    '''Exception for failed retrieval of an HTML parse tree for a part.'''
    pass


def get_digikey_part_html_tree(pn, url=None):
    '''Find the Digikey HTML page for a part number and return the parse tree.'''
    #url='https://www.google.com/search?q=pic18f14k50-I%2FSS-ND+site%3Adigikey.com'
    #url = 'http://www.digikey.com/product-search/en?WT.z_homepage_link=hp_go_button&lang=en&site=us&keywords=' + URLL.quote(pn,safe='')
    #url = 'http://www.digikey.com/product-detail/en/PIC18F14K50T-I%2FSS/PIC18F14K50T-I%2FSSCT-ND/5013555'

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://www.digikey.com/scripts/DkSearch/dksus.dll?WT.z_header=search_go&lang=en&keywords=' + URLL.quote(
            pn,
            safe='')
    elif url[0] == '/':
        url = 'http://www.digikey.com' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    url_opener = FakeBrowser()
    html = url_opener.open(url).read()
    tree = BS.BeautifulSoup(html)

    # If the tree contains the tag for a product page, then just return it.
    if tree.find('html', class_='rd-product-details-page') is not None:
        return tree

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('html', class_='rd-product-category-page') is not None:
        # Look for the table of products.
        products = tree.find('table',
                             class_='stickyHeader',
                             id='productTable').find('tbody').find_all('tr')

        # Extract the product links for the part numbers from the table.
        product_links = [p.find('td',
                                class_='digikey-partnumber').a
                         for p in products]

        # Extract all the part numbers from the text portion of the links.
        part_numbers = [l.text for l in product_links]

        # Look for the part number in the list that most closely matches the requested part number.
        match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]

        # Now look for the link that goes with the closest matching part number.
        for l in product_links:
            if l.text == match:
                # Get the tree for the linked-to page and return that.
                return get_digikey_part_html_tree(pn, url=l['href'])

            # If the HTML contains a list of part categories, then give up.
    if tree.find('html', class_='rd-search-parts-page') is not None:
        raise PartHtmlError

    # I don't know what happened here, so give up.
    raise PartHtmlError


def get_mouser_part_html_tree(pn, url=None):
    '''Find the Mouser HTML page for a part number and return the parse tree.'''

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://www.mouser.com/Search/Refine.aspx?Keyword=' + URLL.quote(pn, safe='')
    elif url[0] == '/':
        url = 'http://www.mouser.com' + url
    elif url.startswith('..'):
        url = 'http://www.mouser.com/Search/' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    url_opener = FakeBrowser()
    html = url_opener.open(url).read()
    tree = BS.BeautifulSoup(html)

    # If the tree contains the tag for a product page, then just return it.
    if tree.find('div', id='product-details') is not None:
        return tree

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('table', class_='SearchResultsTable') is not None:
        # Look for the table of products.
        products = tree.find(
            'table',
            class_='SearchResultsTable').find_all(
                'tr',
                class_=('SearchResultsRowOdd', 'SearchResultsRowEven'))

        # Extract the product links for the part numbers from the table.
        product_links = [p.find('div', class_='mfrDiv').a for p in products]

        # Extract all the part numbers from the text portion of the links.
        part_numbers = [l.text for l in product_links]

        # Look for the part number in the list that most closely matches the requested part number.
        match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]

        # Now look for the link that goes with the closest matching part number.
        for l in product_links:
            if l.text == match:
                # Get the tree for the linked-to page and return that.
                return get_mouser_part_html_tree(pn, url=l['href'])

    # I don't know what happened here, so give up.
    raise PartHtmlError
