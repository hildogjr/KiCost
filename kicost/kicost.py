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

import sys
import pprint
import re
import difflib
from bs4 import BeautifulSoup
import urllib as URLL
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range, xl_range_abs

DELIMITER = ':'

THIS_MODULE = sys.modules[__name__]

# Global array of distributor names.
distis = ['digikey', 'mouser']


def kicost(infile, qty, outfile):

    # Read-in the schematic XML file to get a tree and get its root.
    print 'Get schematic XML...'
    root = BeautifulSoup(open(infile))

    # Find the parts used from each library.
    print 'Get parts library...'
    libparts = {}
    for p in root.find('libparts').find_all('libpart'):

        # Get the values for the fields in each part (if any).
        fields = {}  # Clear the field dict for this part.
        try:
            for f in p.find('fields').find_all('field'):
                # Store the name and value for each field.
                fields[f['name'].lower()] = f.string
        except AttributeError:
            # No fields found for this part.
            pass

        # Store the field dict under the key made from the
        # concatenation of the library and part names.
        libparts[p['lib'] + DELIMITER + p['part']] = fields

        # Also have to store the fields under any part aliases.
        try:
            for alias in p.find('aliases').find_all('alias'):
                libparts[p['lib'] + DELIMITER + alias.string] = fields
        except AttributeError:
            pass  # No aliases for this part.

    # Find the components used in the schematic and elaborate
    # them with global values from the libraries and local values
    # from the schematic.
    print 'Get components...'
    components = {}
    for c in root.find('components').find_all('comp'):

        # Find the library used for this component.
        libsource = c.find('libsource')

        # Create the key to look up the part in the libparts dict.
        libpart = libsource['lib'] + DELIMITER + libsource['part']

        # Initialize the fields from the global values in the libparts dict entry.
        # (These will get overwritten by any local values down below.)
        fields = libparts[libpart].copy()  # Make a copy! Don't use reference!

        # Store the part key and its value.
        fields['libpart'] = libpart
        fields['value'] = c.find('value').string

        # Get the footprint for the part (if any) from the schematic.
        try:
            fields['footprint'] = c.find('footprint').string
        except AttributeError:
            pass

        # Get the values for any other the fields in the part (if any) from the schematic.
        try:
            for f in c.find('fields').find_all('field'):
                fields[f['name'].lower()] = f.string
        except AttributeError:
            pass

        # Store the fields for the part using the reference identifier as the key.
        ref = c['ref']
        components[c['ref']] = fields

    # Get groups of identical components.
    print 'Get groups of identical components...'
    component_groups = {}
    for c in components:

        # Take the field keys and values of each part and create a hash.
        # Use the hash as the key to a dictionary that stores lists of
        # part references that have identical field values.
        h = hash(tuple(sorted(components[c].items())))

        # Now add the hashed component to the group with the matching hash
        # or create a new group if the hash hasn't been seen before.
        try:
            # Add next ref for identical part to the list.
            # No need to add field values since they are the same as the 
            # starting ref field values.
            component_groups[h].refs.append(c)
        except KeyError:

            class IdenticalComponents:
                pass  # Just need a temporary class here.

            component_groups[h] = IdenticalComponents()  # Add empty structure.
            component_groups[h].refs = [c]  # Init list of refs with first ref.
            component_groups[h].fields = components[c]  # Store field values.

    # Calculate the quantity needed of each part for a single board.
    print 'Calculate required # of each component group...'
    for part in component_groups.values():
        # part quantity = # of identical components per board.
        part.qty = len(part.refs)

    # Get the parsed product pages for each part from each distributor.
    print 'Get parsed product page for each component group...'
    for part in component_groups.values():
        part.html_trees, part.urls = get_part_html_trees(part)

    # Create spreadsheet file.
    with xlsxwriter.Workbook('kicost.xlsx') as workbook:
        wrk_formats = {}
        wrk_formats['global'] = workbook.add_format({
            'font_size': 14,
            'font_color': '#FFFFFF',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#303030'
        })
        wrk_formats['digikey'] = workbook.add_format({
            'font_size': 14,
            'font_color': '#000000',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#FFD320'
        })
        wrk_formats['mouser'] = workbook.add_format({
            'font_size': 14,
            'font_color': '#FFFFFF',
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#004586'
        })
        wrk_formats['header'] = workbook.add_format({
            'font_size': 12,
            'bold': True,
            'align': 'center',
            'valign': 'bottom',
            'text_wrap': True
        })
        wrk_formats['total_cost_label'] = workbook.add_format(
            {'font_size': 14,
             'bold': True,
             'align': 'right'})
        wrk_formats['total_cost_currency'] = workbook.add_format(
            {'font_size': 14,
             'bold': True,
             'num_format': '$#,##0.00'})
        wrk_formats['currency'] = workbook.add_format(
            {'num_format': '$#,##0.00'})
        wrk_formats['centered_text'] = workbook.add_format({'align': 'center'})
        wks = workbook.add_worksheet('Pricing')
        workbook.define_name('BoardQty', '=Pricing!$B$1:$B$1')
        brd_qty_fmt = workbook.add_format(
            {'font_size': 14,
             'bold': True,
             'align': 'right'})
        wks.write(0, 0, 'Board Qty:', brd_qty_fmt)
        wks.write(0, 1, 100, brd_qty_fmt)  # Set initial board quantity to zero.
        start_row = 2
        start_col = 0
        next_col = add_globals_to_worksheet(wks, wrk_formats, start_row,
                                            start_col,
                                            component_groups.values())
        for dist in distis:
            next_col = add_dist_to_worksheet(wks, wrk_formats, start_row,
                                             next_col, dist,
                                             component_groups.values())

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


def sort_refs(refs):
    def convert_to_ranges(nums):
        nums.sort()
        num_ranges = []
        i = 0
        while i < len(nums):
            num_range = nums[i]
            jump_i = i + 1
            for j in range(i + 2, len(nums)):
                if j - i != nums[j] - nums[i]:
                    break
                num_range = [nums[i], nums[j]]
                jump_i = j + 1
            num_ranges.append(num_range)
            i = jump_i
        return num_ranges

    ref_re = re.compile('(?P<id>[a-zA-Z]+)(?P<num>[0-9]+)', re.IGNORECASE)
    ref_numbers = {}
    for r in refs:
        match = re.search(ref_re, r)
        id = match.group('id')
        num = int(match.group('num'))
        try:
            ref_numbers[id].append(num)
        except KeyError:
            ref_numbers[id] = [num]
    for id in ref_numbers.keys():
        ref_numbers[id] = convert_to_ranges(ref_numbers[id])
    sorted_refs = []
    for id, nums in ref_numbers.items():
        for num in nums:
            if type(num) == list:
                sorted_refs.append('{0}{1}-{0}{2}'.format(id, num[0], num[1]))
            else:
                sorted_refs.append('{}{}'.format(id, num))
    return sorted_refs


def add_globals_to_worksheet(wks, wrk_formats, start_row, start_col, parts):
    column_headers = ('Part Refs', 'Value', 'Description', 'Footprint',
                      'Manufacturer', 'Manf Part#', 'Qty Needed', 'Qty Slack')
    num_cols = len(column_headers)
    row = start_row
    
    # Add label for global section.
    wks.merge_range(row, start_col, row, start_col + num_cols - 1, "Globals",
                    wrk_formats['global'])
    row += 1
    
    # Add column headers.
    col = start_col
    for col_header in column_headers:
        wks.write_string(row, col, col_header, wrk_formats['header'])
        col += 1
    row += 1
    
    # Add global data for each part.
    for part in parts:
        col = start_col
        
        # Enter part references.
        wks.write_string(row, col, ','.join(sort_refs(part.refs)))
        col += 1
        
        # Enter more data for the part.
        for field in ('value', 'desc', 'footprint', 'manf', 'manf#'):
            try:
                wks.write_string(row, col, part.fields[field])
            except KeyError:
                pass
            col += 1
            
        # Enter total part quantity needed.
        wks.write(row, col, '=BoardQty*{}'.format(part.qty))
        col += 1
        
        # Enter part slack quantity.
        wks.write(row, col, 0)  # slack quantity. (Not handled, yet.)
        row += 1
        
    # Return column following the globals so we know where to start next set of cells.
    return start_col + num_cols


def add_dist_to_worksheet(wks, wrk_formats, start_row, start_col, dist, parts):
    column_headers = ('Available Qty', 'Purchase Qty', 'Unit Price',
                      'Extended Price', 'Digikey Part#', 'Catalog Page')
    num_cols = len(column_headers)
    row = start_row
    
    # Add label for this distributor.
    wks.merge_range(row, start_col, row, start_col + num_cols - 1, dist,
                    wrk_formats[dist])
    row += 1
    
    # Add column headers.
    col = start_col
    for col_header in column_headers:
        wks.write_string(row, col, col_header, wrk_formats['header'])
        col += 1
    row += 1
    
    # Add distributor data for each part.
    for part in parts:
        col = start_col
        
        # Enter quantity of part available at this distributor.
        get_dist_qty_avail = getattr(THIS_MODULE,
                                     'get_{}_qty_avail'.format(dist))
        wks.write(row, col, get_dist_qty_avail(part.html_trees[dist]))
        col += 1
        
        # Enter quantity of this part that's needed.
#        wks.write(row, col, '=IF(LEN({})=0,"",{})'.format(
        wks.write(row, col, ''.format(
            xl_rowcol_to_cell(row, start_col + 4), xl_rowcol_to_cell(row, 6))
                  )  # Show global quantity if distributor part# exists, else blank.
        col += 1
        
        # Get function for extracting the price tiers from the distributor HTML page tree.
        get_dist_price_tiers = getattr(THIS_MODULE,
                                       'get_{}_price_tiers'.format(dist))
                                       
        # Extract price tiers from distributor HTML page tree.
        price_tiers = get_dist_price_tiers(part.html_trees[dist])
        
        # Sort the quantity breaks and prices and turn them into strings.
        qtys = sorted(price_tiers.keys())
        prices = [str(price_tiers[q]) for q in qtys]
        qtys = [str(q) for q in qtys]
        
        # Enter a lookup function that determines the unit price based on purchased quantity.
        needed_qty_col = 6 
        lookup_func = '=iferror(lookup({},{{{}}},{{{}}}),"")'.format(
            xl_rowcol_to_cell(row, needed_qty_col), ','.join(qtys), ','.join(prices))
        wks.write_formula(row, col, lookup_func, wrk_formats['currency'])
        col += 1
        
        # Enter the formula for the extended price = qty * unit price.
        wks.write_formula(row, col, '=iferror({}*{},"")'.format(
            xl_rowcol_to_cell(row, needed_qty_col), xl_rowcol_to_cell(row, col - 1)),
                          wrk_formats['currency'])
        col += 1
        
        # Enter distributor part number for ordering purposes.
        get_dist_part_num = getattr(THIS_MODULE, 'get_{}_part_num'.format(dist))
        dist_part_num = get_dist_part_num(part.html_trees[dist])
        wks.write(row, col, dist_part_num)
        col += 1
        
        # Enter a link to the distributor webpage for this part.
        if len(dist_part_num) > 0:
            wks.write_url(row, col, part.urls[dist],
                          wrk_formats['centered_text'],
                          string='Link')
        row += 1
        
    # Sum the extended prices for all the parts to get the total cost from this distributor.
    wks.write(row, start_col + 2, 'Total Cost:',
              wrk_formats['total_cost_label'])
    wks.write(row, start_col + 3, '=sum({})'.format(
        xl_range(start_row + 2, start_col + 3, row - 1, start_col + 3)),
              wrk_formats['total_cost_currency'])
              
    # Add list of part numbers and purchase quantities for ordering purposes.
    qty_col = start_col + 1
    def enter_order_info(info_col, order_col):
        num_parts = len(parts)
        order_start_row = start_row + 1 + 1 + num_parts + 1 + 3
        data_row = start_row + 2
        formula = '''
            IFERROR(
                INDEX(
                    {get_range},
                    SMALL(
                        IF(
                            {sel_range} <> "",
                            ROW({sel_range}) - MIN(ROW({sel_range})) + 1,
                            ""
                        ),
                        ROW()-ROW({order_start_row})+1
                    )
                ),
                ""
            )
        '''
        formula = re.sub('[\s\n]','',formula)
        wks.write_array_formula(
                xl_range(order_start_row, order_col, order_start_row+num_parts-1, order_col),
                '{{={formula}}}'.format(formula=formula.format(
                order_start_row=xl_rowcol_to_cell(order_start_row, order_col, row_abs=True),
                sel_range=xl_range_abs(data_row, qty_col, data_row+num_parts-1, qty_col),
                get_range=xl_range_abs(data_row, info_col, data_row+num_parts-1, info_col)
                ))
        )
    part_num_col = start_col + 4
    order_qty_col = start_col + 1
    order_part_num_col = order_qty_col + 1
    enter_order_info(qty_col,      order_qty_col)
    enter_order_info(part_num_col, order_part_num_col)
             
    return start_col + num_cols  # Return column following the globals so we know where to start next set of cells.



def get_digikey_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Digikey product page.'''
    price_tiers = {}
    try:
        for tr in html_tree.find(id='pricing').find_all('tr'):
            try:
                td = tr.find_all('td')
                qty = int(re.sub('[^0-9]', '', td[0].text))
                price_tiers[qty] = float(re.sub('[^0-9\.]', '', td[1].text))
            except IndexError:  # Happens when there's no <td> in table row.
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        price_tiers[0] = 0.00
        return price_tiers  # Return the quantity-zero pricing.
    min_qty = min(price_tiers.keys())
    if min_qty > 1:
        price_tiers[1] = price_tiers[min_qty]
    price_tiers[0] = 0.00  # Add zero-quantity level so LOOKUP function works sensibly.
    return price_tiers


def get_mouser_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the Mouser product page.'''
    price_tiers = {}
    try:
        for tr in html_tree.find('table', class_='PriceBreaks').find_all('tr'):
            try:
                qty = int(re.sub('[^0-9]', '',
                                 tr.find('td',
                                         class_='PriceBreakQuantity').a.text))
                unit_price = tr.find('td', class_='PriceBreakPrice').span.text
                price_tiers[qty] = float(re.sub('[^0-9\.]', '', unit_price))
            except (TypeError, AttributeError, ValueError):
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        price_tiers[0] = 0.00
        return price_tiers  # Return the quantity-zero pricing.
    min_qty = min(price_tiers.keys())
    if min_qty > 1:
        price_tiers[1] = price_tiers[min_qty]
    price_tiers[0] = 0.00  # Add zero-quantity level so LOOKUP function works sensibly.
    return price_tiers


def get_digikey_part_num(html_tree):
    try:
        return re.sub('\n', '', html_tree.find('td', id='reportpartnumber').text)
    except AttributeError:
        return ''


def get_mouser_part_num(html_tree):
    try:
        return re.sub('\n', '', html_tree.find('div', id='divMouserPartNum').text)
    except AttributeError:
        return ''


def get_digikey_qty_avail(html_tree):
    try:
        qty_str = html_tree.find('td', id='quantityavailable').text
        qty_str = re.search('(?<=stock: )[0-9,]*', qty_str,
                            re.IGNORECASE).group(0)
        return int(re.sub('[^0-9]', '', qty_str))
    except AttributeError:
        return ''


def get_mouser_qty_avail(html_tree):
    try:
        qty_str = html_tree.find(
            'table',
            id='ctl00_ContentMain_availability_tbl1').find_all('td')[0].text
        return int(re.sub('[^0-9]', '', qty_str))
    except AttributeError:
        return ''


def get_part_html_trees(part):
    '''Get the parsed HTML trees from each distributor website for the given part.'''
    html_trees = {}
    urls = {}
    fields = part.fields
    for dist in distis:
        get_dist_part_html_tree = getattr(THIS_MODULE,
                                          'get_{}_part_html_tree'.format(dist))
        try:
            if dist + '#' in fields:
                html_trees[dist], urls[dist] = get_dist_part_html_tree(
                    fields[dist + '#'])
            elif 'manf#' in fields:
                html_trees[dist], urls[dist] = get_dist_part_html_tree(
                    fields['manf#'])
            else:
                raise PartHtmlError
        except PartHtmlError, AttributeError:
            html_trees[dist] = BeautifulSoup('<html></html>')
            urls[dist] = ''
    return html_trees, urls


class FakeBrowser(URLL.FancyURLopener):
    ''' This is a fake browser string so the distributor websites will talk to us.'''
    version = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.124 Safari/537.36'


class PartHtmlError(Exception):
    '''Exception for failed retrieval of an HTML parse tree for a part.'''
    pass


def merge_digikey_price_tiers(main_tree, alt_tree):
    '''Merge the price tiers from the alternate-packaging tree into the main tree.'''
    try:
        insertion_point = main_tree.find('table', id='pricing').find('tr')
        for tr in alt_tree.find('table', id='pricing').find_all('tr'):
            insertion_point.insert_after(tr)
    except AttributeError:
        pass


def get_digikey_part_html_tree(pn, url=None, descend=2):
    '''Find the Digikey HTML page for a part number and return the URL and parse tree.'''
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
    tree = BeautifulSoup(html)

    # If the tree contains the tag for a product page, then return it.
    if tree.find('html', class_='rd-product-details-page') is not None:

        # Digikey separates cut-tape and reel packaging, so we need to examine more pages 
        # to get all the pricing info. But don't descend into any further if limit has been reached.
        if descend > 0:
            try:

                # Find all the URLs to alternate-packaging pages for this part.
                alt_packaging_urls = [
                    ap.find('td',
                            class_='lnkAltPack').a['href']
                    for ap in tree.find(
                        'table',
                        class_='product-details-alternate-packaging').find_all(
                            'tr',
                            class_='more-expander-item')
                ]

                for ap_url in alt_packaging_urls:
                    try:
                        # Get the parse tree for each alternate-packaging page...
                        ap_tree, waste_url = get_digikey_part_html_tree(
                            pn,
                            url=ap_url,
                            descend=0)
                        # and merge the pricing info from that into the main parse tree to make
                        # a single, unified set of price tiers.
                        merge_digikey_price_tiers(tree, ap_tree)
                    except AttributeError:
                        continue
            except AttributeError:
                pass
        return tree, url  # Return the parse tree and the URL where it came from.

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('html', class_='rd-product-category-page') is not None:
        if descend <= 0:
            raise PartHtmlError
        else:
            # Look for the table of products.
            products = tree.find(
                'table',
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
                    return get_digikey_part_html_tree(pn,
                                                      url=l['href'],
                                                      descend=descend - 1)

    # If the HTML contains a list of part categories, then give up.
    if tree.find('html', class_='rd-search-parts-page') is not None:
        raise PartHtmlError

    # I don't know what happened here, so give up.
    raise PartHtmlError


def get_mouser_part_html_tree(pn, url=None):
    '''Find the Mouser HTML page for a part number and return the URL and parse tree.'''

    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://www.mouser.com/Search/Refine.aspx?Keyword=' + URLL.quote(
            pn,
            safe='')
    elif url[0] == '/':
        url = 'http://www.mouser.com' + url
    elif url.startswith('..'):
        url = 'http://www.mouser.com/Search/' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    url_opener = FakeBrowser()
    html = url_opener.open(url).read()
    tree = BeautifulSoup(html)

    # If the tree contains the tag for a product page, then just return it.
    if tree.find('div', id='product-details') is not None:
        return tree, url

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
