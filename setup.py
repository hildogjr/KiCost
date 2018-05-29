#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools
import kicost

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Update the information files that stay in the computer.
with open('README.rst') as readme_file:
    readme = readme_file.read()
with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

# KiCost Python packages requirements to run-time.
requirements = [
    'beautifulsoup4 >= 4.3.2',
    'XlsxWriter >= 0.7.3',
    'future >= 0.15.0',
    'lxml >= 3.7.2',
    'yattag >= 1.5.2',
    'tqdm >= 4.4.0',
    'CurrencyConverter >= 0.5', # It will be decreped on next release!
    'pycountry >= 18.2', # ISO4117, ISO3166 country and currency definitons from Debian’s pkg-isocodes.
#    'wxPython >= 4.0', # Graphical package/library needed to user guide.
]

# KiCost Python packages requirements to debug and tests.
test_requirements = [
    # TODO: put package test requirements here
]

# Extra files needed by KiCost.
data_files=[
    #('kicost', ['kicost/kicost.ico']), # Icon to the user guide. Added via `MANIFEST.in`
],

setup(
    name='kicost',
    version=kicost.__version__,
    description="Build cost spreadsheet for a KiCad project.",
    long_description=readme + '\n\n' + history,
    long_description_content_type="text/markdown",
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
    keywords='kicost, KiCAD',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
