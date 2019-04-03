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

# Author information.
__author__ = 'Hildo Guillardi Júnior'
__webpage__ = 'info@xess.com's

# Libraries.
import json, requests
import logging, tqdm
import copy, re
from collections import Counter
from urllib.parse import quote_plus as urlquote

# KiCost definitions.
from .global_vars import * # Debug information, `distributor_dict` and `SEPRTR`.

# Distributors definitions.
from .distributor import distributor_class

from currency_converter import CurrencyConverter
currency_convert = CurrencyConverter().convert

MAX_PARTS_BY_QUERY = 20 # Maximum part list length to one single query.

QUERY_ANSWER = '''
    mpn{manufacturer, part},
    type,
    datasheet,
    description,
    image{url, credit_string, credit_url},
    specs{key, name, value},
    offers{
      sku {vendor, part},
      description,
      moq,
      in_stock_quantity,
      stock_location,
      image {url, credit_string, credit_url},
      specs {key, name, value},
      prices{GBP, EUR USD}
'''
QUERY_ANSWER = re.sub('[\s\n]', '', QUERY_ANSWER)

QUERY_PART = 'query ($input: MpnInput!) { part(mpn: $input) { {ANS} }'.format(ANS=QUERY_ANSWER)
QUERY_MATCH = 'query ($input: [MpnOrSku]!){ match(parts: $input) { {ANS} }'.format(ANS=QUERY_ANSWER)
QUERY_SEARCH = 'query ($input: String!){ search(term: $input) { {ANS} }'.format(ANS=QUERY_ANSWER)

KITSPACE_WEB = "https://dev-partinfo.kitspace.org/graphql"

__all__ = ['query']



r = requests.post("https://dev-partinfo.kitspace.org/graphql", {"query": QUERY_MATCH, "variables": variables})