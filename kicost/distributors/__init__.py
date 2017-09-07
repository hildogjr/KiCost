# -*- coding: utf-8 -*-

__author__ = 'XESS Corporation'
__email__ = 'info@xess.com'

# The global dictionary of distributor information starts out empty.
distributors = {}

import os

# The distributor module directories will be found in this directory.
directory = os.path.dirname(__file__)

# Search for the distributor modules and import them.
for module in os.listdir(os.path.dirname(__file__)):

    # Avoid importing non-directories.
    abs_module = os.path.join(directory, module)
    if not os.path.isdir(abs_module):
        continue

    # Avoid directories like __pycache__.
    if module.startswith('__'):
        continue

    # Import the module.
    __import__(module, globals(), locals(), [], level=1)
