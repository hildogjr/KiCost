#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools
import kicost

import re
SHOW_LAST_HISTORY=3

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Update the information files that stay in the computer.
with open('README.rst') as readme_file:
    readme = readme_file.read()
with open('HISTORY.rst') as history_file:
    history = history_file.read()
    try:
        history = history.replace('.. :changelog:', '')
        #update_format = r'(^[\s.]*History\s*[\=\-\_]+\s+((?:\s|.)*?\n[\=\-\_]+\s*(?:\s|.)+?\s*){{{n}}})\s+[\d\.]+(?:\s|.)*?\s*[\=\-\_]+'.format(n=SHOW_LAST_HISTORY)
        #history = re.findall(update_format, history)[0][0]
        #if SHOW_LAST_HISTORY==1:
        #    history = history.replace('History', 'Latest update')
        #else:
        #    history = history.replace('History', 'Latest updates')
        #history = history + '\n\nAccess https://github.com/xesscorp/KiCost/blob/master/HISTORY.rst for full development history.'
    except:
        pass

# KiCost Python packages requirements to run-time.
requirements = [
    'beautifulsoup4 >= 4.3.2', # Deal with HTML and XML tags.
    'XlsxWriter >= 0.7.3', # Write the XLSX output file.
    'future', # For print statements.
    'tqdm >= 4.30.0', # Progress bar.
    'requests >= 2.18.4', # Scrape, API and web modules.
    'CurrencyConverter >= 0.13', # Used to convert price to a not available currency in one distributor.
    'babel >= 2.6', # For currency format by the language in the spreadsheet.
#    'wxPython >= 4.0', # Graphical package/library needed to user guide.
]

# KiCost Python packages requirements to debug and tests.
test_requirements = [
    # Put package test requirements here.
]

# Extra files needed by KiCost.
data_files=[
    #('kicost', ['kicost/kicost.ico']), # Icon to the user guide. Added via `MANIFEST.in`.
]

setup(
    name='kicost',
    version=kicost.__version__,
    description="Build cost spreadsheet for a KiCad project.",
    long_description=readme + '\n\n' + history,
#    long_description_content_type="text/reStructuredText",
    author=kicost.__author__,
    author_email=kicost.__email__,
    url='https://xesscorp.github.io/KiCost',
    project_urls={
        'Doc': 'https://xesscorp.github.io/KiCost',
        'Git': 'https://github.com/xesscorp/KiCost',
    },
    packages=setuptools.find_packages(),
    entry_points={'console_scripts':['kicost = kicost.__main__:main']},
    package_dir={'kicost':'kicost'},
    include_package_data=True,
    package_data={'kicost': ['*.gif', '*.png']},
    #data_files=data_files,
    scripts=[],
    install_requires=requirements,
    license="MIT",
    zip_safe=False,
    keywords='KiCAD, BOM, electronics',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)

# Run the KiCost integration script.
try:
    import sys
    if sys.platform.startswith("win32"):
        # For Windows it is necessary one additional library (used to create the shortcut).
        try:
            from pip import main as pipmain
        except ImportError:
            from pip._internal import main as pipmain
        pipmain(['install', 'pywin32'])
    # Run setup: shortcut, BOM module to Eeschema and OS context menu.
    from .kicost.kicost_config import kicost_setup
    kicost_setup()
except:
    print('Error to run KiCost integration script.')