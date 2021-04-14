#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) 2021 Salvador E. Tropea
# Copyright (c) 2021 Instituto Nacional de Tecnología Industrial
# License: Apache 2.0
# Project: KiCost
"""
Simple helper to download the exchange rates.
"""
import os
import sys
from bs4 import BeautifulSoup

if sys.version_info[0] < 3:
    from urllib2 import urlopen, URLError
else:
    from urllib.request import urlopen, URLError

# Author information.
__author__ = 'Salvador Eduardo Tropea'
__webpage__ = 'https://github.com/set-soft/'
__company__ = 'INTI-CMNB - Argentina'

url = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'


def download_rates():
    content = ''
    if os.environ.get('KICOST_CURRENCY_RATES'):
        with open(os.environ['KICOST_CURRENCY_RATES'], 'rt') as f:
            content = f.read()
    else:
        try:
            content = urlopen(url).read().decode('utf8')
        except URLError:
            pass
    soup = BeautifulSoup(content, 'xml')
    rates = {'EUR': 1.0}
    date = ''
    for entry in soup.find_all('Cube'):
        currency = entry.get('currency')
        if currency is not None:
            rates[currency] = float(entry.get('rate'))
        elif entry.get('time'):
            date = entry.get('time')
    return date, rates
