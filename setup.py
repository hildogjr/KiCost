#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools
import kicost


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    'beautifulsoup4 >= 4.3.2',
    'XlsxWriter >= 0.7.3',
    'future >= 0.15.0',
    'lxml >= 3.3.5',
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='kicost',
    version=kicost.__version__,
    description="Build cost spreadsheet for a KiCad project.",
    long_description=readme + '\n\n' + history,
    author=kicost.__author__,
    author_email=kicost.__email__,
    url='https://github.com/xesscorp/KiCost',
#    packages=['kicost',],
    packages=setuptools.find_packages(),
    entry_points={'console_scripts':['kicost = kicost.__main__:main']},
    package_dir={'kicost':'kicost'},
    include_package_data=True,
    package_data={'kicost': ['*.gif', '*.png']},
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
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
