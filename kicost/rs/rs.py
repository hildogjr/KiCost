# Inserted by Pasteurize tool.
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from builtins import zip
from builtins import range
from builtins import int
from builtins import str
from future import standard_library
standard_library.install_aliases()

import future

import sys
import pprint
import re
import difflib
import logging
import tqdm
from bs4 import BeautifulSoup
from random import randint
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell, xl_range, xl_range_abs
from yattag import Doc, indent  # For generating HTML page for local parts.
import multiprocessing
from multiprocessing import Pool # For running web scrapes in parallel.
import http.client # For web scraping exceptions.

try:
    from urllib.parse import urlencode, quote as urlquote, urlsplit, urlunsplit
    import urllib.request
    from urllib.request import urlopen, Request
except ImportError:
    from urlparse import quote as urlquote, urlsplit, urlunsplit
    from urllib import urlencode
    from urllib2 import urlopen, Request
    
from ..kicost import PartHtmlError, FakeBrowser

from currency_converter import CurrencyConverter

__author__='Giacinto Luigi Cerone'

HTML_RESPONSE_RETRIES = 2 # Num of retries for getting part data web page.

WEB_SCRAPE_EXCEPTIONS = (urllib.request.URLError, http.client.HTTPException)

currency = CurrencyConverter()

#~ def get_user_agent():
    #~ # The default user_agent_list comprises chrome, IE, firefox, Mozilla, opera, netscape.
    #~ # for more user agent strings,you can find it in http://www.useragentstring.com/pages/useragentstring.php
    #~ user_agent_list = [
        #~ "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
        #~ "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",
        #~ "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",
        #~ "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",
        #~ "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",
        #~ "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",
        #~ "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",
        #~ "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        #~ "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        #~ "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",
        #~ "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        #~ "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",
        #~ "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        #~ "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        #~ "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",
        #~ "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",
        #~ "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
        #~ "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24"
    #~ ]
    #~ return user_agent_list[randint(0, len(user_agent_list) - 1)]

#~ def FakeBrowser(url):
    #~ req = Request(url)
    #~ req.add_header('Accept-Language', 'en-US')
    #~ req.add_header('User-agent', get_user_agent())
    #~ return req


#~ class PartHtmlError(Exception):
    #~ '''Exception for failed retrieval of an HTML parse tree for a part.'''
    #~ pass

def get_rs_price_tiers(html_tree):
    '''Get the pricing tiers from the parsed tree of the RS Components product page.'''
    price_tiers = {}
    
    try:
        qty_strs = []
        for qty in html_tree.find_all('div',class_='breakRangeWithoutUnit', itemprop='eligibleQuantity'):
            qty_strs.append(qty.text)
        price_strs = []
        for price in html_tree.find_all('div', class_='unitPrice'):
            if price.text is not u'':
                price_strs.append(price.text)
        qtys_prices = list(zip(qty_strs, price_strs))
        for qty_str, price_str in qtys_prices:
            try:
                qty = re.search('(\s*)([0-9,]+)', qty_str).group(2)
                qty = int(re.sub('[^0-9]', '', qty))
                price_str=price_str.replace(',','.')
                price_tiers[qty] = float(re.sub('[^0-9\.]', '', price_str))
                price_tiers[qty] = currency.convert(price_tiers[qty], 'EUR', 'USD')
            except (TypeError, AttributeError, ValueError):
                continue
    except AttributeError:
        # This happens when no pricing info is found in the tree.
        return price_tiers  # Return empty price tiers.
    return price_tiers
    
def get_rs_part_num(html_tree):
    '''Get the part number from the farnell product page.'''
    try:
        pn_str = html_tree.find('span', class_='keyValue bold', itemprop='sku').text
        pn = re.sub('[^0-9\-]','', pn_str)
        return pn
    except KeyError:
        return 'no part number found' # No catalog number found in page.
    except AttributeError:
        return 'no part number found' # No ProductDescription found in page.

def get_rs_qty_avail(html_tree):
    '''Get the available quantity of the part from the farnell product page.'''
        
    try:
        # Note that 'availability' is misspelled in the container class name!        
        qty_str = html_tree.find('div', class_='floatLeft stockMessaging availMessageDiv bottom5').text
    except (AttributeError, ValueError):
        print('no quantity')
        # No quantity found (not even 0) so this is probably a non-stocked part.
        # Return None so the part won't show in the spreadsheet for this dist.
        return None
    try:
        qty = re.sub('[^0-9]','',qty_str[0:10])  # Strip all non-number chars.
        return int(qty)  # Return integer for quantity.
    except ValueError:
        # No quantity found (not even 0) so this is probably a non-stocked part.
        # Return None so the part won't show in the spreadsheet for this dist.
        return None

def get_rs_part_html_tree(dist, pn, extra_search_terms='', url=None, descend=2):
    '''Find the RS Components HTML page for a part number and return the URL and parse tree.'''
            
    # Use the part number to lookup the part using the site search function, unless a starting url was given.
    if url is None:
        url = 'http://it.rs-online.com/web/c/?searchTerm=' + urlquote(pn + ' ' + extra_search_terms, safe='')

    elif url[0] == '/':
        url = 'http://it.rs-online.com' + url
    elif url.startswith('..'):
        url = 'http://it.rs-online.com/Search/' + url

    # Open the URL, read the HTML from it, and parse it into a tree structure.
    for _ in range(HTML_RESPONSE_RETRIES):
        try:
            req = FakeBrowser(url)
            response = urlopen(req)
            html = response.read()
            break
        except WEB_SCRAPE_EXCEPTIONS:
            logger.log(DEBUG_DETAILED,'Exception while web-scraping {} from {}'.format(pn, dist))
            pass
    else: # Couldn't get a good read from the website.
        raise PartHtmlError
    tree = BeautifulSoup(html, 'lxml')
        
    # If the tree contains the tag for a product page, then just return it.
    if tree.find('div', class_='specTableContainer') is not None:
        return tree, url

    # If the tree is for a list of products, then examine the links to try to find the part number.
    if tree.find('div', class_='srtnPageContainer') is not None:
        if descend <= 0:
            raise PartHtmlError
        else:
            # Look for the table of products.
            products = tree.find_all('tr', class_='resultRow')

            # Extract the product links for the part numbers from the table.
            product_links= []
            for p in products:
                try:
                    product_links.append('http://it.rs-online.com'+p.find('a',class_='tnProdDesc')['href'])
                    # Up to now get the first url found in the list. i.e. do not choose the url based on the stock type (e.g. single unit, reel etc.)
                    return get_rs_part_html_tree(dist, pn, extra_search_terms,url=product_links[0], descend=descend-1)
                except AttributeError:
                    continue
                except TypeError:
                    #~ print('****************dist:',dist,'pn:**************************',pn)
                    continue
            
            

    #~ # If the tree is for a list of products, then examine the links to try to find the part number.
    #~ if tree.find('div', class_='srtnPageContainer') is not None:
        #~ if descend <= 0:
            #~ raise PartHtmlError
        #~ else:
            #~ # Look for the table of products.
            #~ products = tree.find('table',
                                 #~ class_='productLister',
                                 #~ id='sProdList').find_all('tr',
                                                          #~ class_='altRow')

            #~ # Extract the product links for the part numbers from the table.
            #~ product_links = []
            #~ for p in products:
                #~ try:
                    #~ product_links.append(
                        #~ p.find('td',
                               #~ class_='mftrPart').find('p',
                                                       #~ class_='wordBreak').a)
                #~ except AttributeError:
                    #~ continue

            #~ # Extract all the part numbers from the text portion of the links.
            #~ part_numbers = [l.text for l in product_links]

            #~ # Look for the part number in the list that most closely matches the requested part number.
            #~ match = difflib.get_close_matches(pn, part_numbers, 1, 0.0)[0]

            #~ # Now look for the link that goes with the closest matching part number.
            #~ for l in product_links:
                #~ if l.text == match:
                    #~ # Get the tree for the linked-to page and return that.
                    #~ return get_rs_part_html_tree(dist, pn, extra_search_terms,
                                #~ url=l['href'], descend=descend-1)

    # I don't know what happened here, so give up.
    raise PartHtmlError

if __name__=='__main__':
	
	#~ html_tree=get_rs_part_html_tree(dist='rs',pn='MSP430F5438AIPZ')
	#~ html_tree=get_rs_part_html_tree(dist='rs',pn='CC3200-LAUNCHXL')
    #~ html_tree=get_rs_part_html_tree(dist='rs',pn='LM358PW')
    html_tree=get_rs_part_html_tree(dist='rs',pn='MCP1252-33X50I/MS')
    
    pt=get_rs_price_tiers(html_tree[0])
    qt=get_rs_qty_avail(html_tree[0])
    pn=get_rs_part_num(html_tree[0])
    print('****************')
    print(pt)
    print('****************')
    print(qt)
    print('****************')
    print(pn)
    print('****************')
    
    
