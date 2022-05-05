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

# Simple wrappers for the log functions in the distributors module

from .distributor import distributor_class
from .. import DEBUG_OVERVIEW, DEBUG_DETAILED, DEBUG_OBSESSIVE, DEBUG_FULL


def debug_detailed(*args):
    distributor_class.logger.log(DEBUG_DETAILED, *args)


def debug_overview(*args):
    distributor_class.logger.log(DEBUG_OVERVIEW, *args)


def debug_obsessive(*args):
    distributor_class.logger.log(DEBUG_OBSESSIVE, *args)


def debug_full(*args):
    distributor_class.logger.log(DEBUG_FULL, *args)


def is_debug_full():
    return distributor_class.logger.getEffectiveLevel() <= DEBUG_FULL


def warning(code, msg):
    distributor_class.logger.warning(code + msg)
