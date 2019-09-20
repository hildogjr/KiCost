# -*- coding: utf-8 -*-

# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Júnior
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

"""Stuff that everybody else needs to know about."""

PLATFORM_WINDOWS_STARTS_WITH = 'win32'
PLATFORM_LINUX_STARTS_WITH = 'linux'
PLATFORM_MACOS_STARTS_WITH = 'darwin'


import logging

# The root logger of the application. This has to be the root logger to catch
# output from libraries (e.g. requests) as well.
logger = logging.getLogger('')

DEBUG_OVERVIEW = logging.DEBUG
DEBUG_DETAILED = logging.DEBUG-1
DEBUG_OBSESSIVE = logging.DEBUG-2
DEBUG_HTTP_HEADERS = logging.DEBUG-3
DEBUG_HTTP_RESPONSES = logging.DEBUG-4
# Minimum possible log level is logging.DEBUG-9 !

SEPRTR = ':'  # Delimiter between library:component, distributor:field, etc.

DEFAULT_LANGUAGE = 'en_US' # Default language used by GUI and spreadsheet
                           # generation and number presentation.
DEFAULT_CURRENCY = 'USD' # Default currency assigned.

class PartHtmlError(Exception):
    '''Exception for failed retrieval of an HTML parse tree for a part.'''
    pass

class wxPythonNotPresent(Exception):
    '''Exception for failed retrieval of an HTML parse tree for a part.'''
    pass
