# -*- coding: utf-8 -*-
# MIT license
#
# Copyright (C) 2022 by Salvador E. Tropea / Instituto Nacional de Tecnologia Industrial
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

# Simple wrappers for the log functions in the main module

import logging

DEBUG_OVERVIEW = logging.DEBUG
DEBUG_DETAILED = logging.DEBUG-1
DEBUG_OBSESSIVE = logging.DEBUG-2
DEBUG_HTTP_HEADERS = logging.DEBUG-3
DEBUG_HTTP_RESPONSES = logging.DEBUG-4
DEBUG_FULL = logging.DEBUG-9
# Minimum possible log level is logging.DEBUG-9 !


# The root logger of the application. This has to be the root logger to catch
# output from libraries (e.g. requests) as well.
main_logger = None


def debug(*args):
    main_logger.log(*args)


def debug_detailed(*args):
    main_logger.log(DEBUG_DETAILED, *args)


def is_debug_detailed():
    return main_logger.getEffectiveLevel() <= DEBUG_DETAILED


def debug_overview(*args):
    main_logger.log(DEBUG_OVERVIEW, *args)


def is_debug_overview():
    return main_logger.getEffectiveLevel() <= DEBUG_OVERVIEW


def debug_obsessive(*args):
    main_logger.log(DEBUG_OBSESSIVE, *args)


def is_debug_obsessive():
    return main_logger.getEffectiveLevel() <= DEBUG_OBSESSIVE


def debug_full(*args):
    main_logger.log(DEBUG_FULL, *args)


def debug_general(*args):
    main_logger.debug(*args)


def info(*args):
    main_logger.info(*args)


def warning(code, msg):
    main_logger.warning(code + msg)


def error(*args):
    main_logger.error(*args)


def get_logger():
    global main_logger
    return main_logger


def set_logger(logger):
    global main_logger
    main_logger = logger
