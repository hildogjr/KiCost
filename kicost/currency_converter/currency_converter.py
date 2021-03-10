#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) 2021 Salvador E. Tropea
# Copyright (c) 2021 Instituto Nacional de Tecnología Industrial
# License: Apache 2.0
# Project: KiCost
# Adapted from: https://github.com/alexprengere/currencyconverter
"""
CurrencyConverter:
This is reduced version of the 'Currency Converter' by Alex Prengère.
Original project: https://github.com/alexprengere/currencyconverter

This version only supports conversions for the last exchange rates, not
historic ones.

On the other hand this version always tries to get the last rates.
"""
try:
    from .default_rates import default_rates, default_date
except ImportError:
    # Only useful to boostrap
    default_rates = {}
    default_date = ''
from .download_rates import download_rates

# Author information.
__author__ = 'Salvador Eduardo Tropea'
__webpage__ = 'https://github.com/set-soft/'
__company__ = 'INTI-CMNB - Argentina'


class CurrencyConverter(object):
    def __init__(self):
        self.initialized = False

    def _do_init(self):
        if self.initialized:
            return
        self.date, self.rates = download_rates()
        if not self.date:
            self.date = default_date
            self.rates = default_rates
        self.initialized = True

    def convert(self, amount, currency, new_currency='EUR'):
        """Convert amount from a currency to another one.

        :param float amount: The amount of `currency` to convert.
        :param str currency: The currency to convert from.
        :param str new_currency: The currency to convert to.

        :return: The value of `amount` in `new_currency`.
        :rtype: float

        >>> c = CurrencyConverter()
        >>> c.convert(100, 'EUR', 'USD')
        """
        self._do_init()
        for c in currency, new_currency:
            if c not in self.rates:
                raise ValueError('{0} is not a supported currency'.format(c))

        r0 = self.rates[currency]
        r1 = self.rates[new_currency]

        return float(amount) / r0 * r1
