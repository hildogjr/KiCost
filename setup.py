#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools, os
import kicost

import re
SHOW_LAST_HISTORY=3

try:
    from setuptools import setup
    from setuptools.command.develop import develop
    from setuptools.command.install import install
except ImportError:
    from distutils.core import setup
    from distutils.core.command.develop import develop
    from distutils.core.command.install import install


def post_install_setup():
    # Run the KiCost integration script.
    try:
        import sys
        if sys.platform.startswith("win32"):
            # For Windows it is necessary one additional library (used to create the shortcut).
            print('Installing additional library need for Windows setup...')
            try:
                if sys.version_info < (3,0):
                    from pip._internal import main as pipmain
                else:
                    from pip import main as pipmain
                pipmain(['install', 'pywin32'])
            except:
                print('Error to install Windows additional Python library. KiCost configuration related to Windows registry may not work.')
        # Run setup: shortcut, BOM module to Eeschema and OS context menu.
        try:
            from .kicost.kicost_config import kicost_setup
            kicost_setup()
        except:
            print('Running the external configuration command...')
            from subprocess import call
            call(['kicost', '--setup'])
    except:
        print('Error to run KiCost integration script.')


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        post_install_setup
        develop.run(self)

class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        post_install_setup
        install.run(self)

# Update the information files that stay in the computer.
with open('README.rst') as readme_file:
    readme = readme_file.read()
with open(os.path.join('kicost','HISTORY.rst')) as history_file:
    history = history_file.read()
    try:
        history_full = history.replace('.. :changelog:', '')
        update_format = r'History\s\-+\s(.|\n|\r|\_)*?((.|\n|\r)*?\s{2,}){'+str(SHOW_LAST_HISTORY)+'}'
        history_lastest = re.findall(update_format, history_full)[0][0]
        if history_lastest:
            if SHOW_LAST_HISTORY==1:
                history_lastest = history_lastest.replace('History', 'Latest update')
            else:
                history_lastest = history_lastest.replace('History', 'Latest updates')
            history = history_lastest + '\n\nAccess https://github.com/xesscorp/KiCost/blob/master/HISTORY.rst for full development history.'
        else:
            history = history_full
    except:
        history = history_full
        pass

# KiCost Python packages requirements to run-time.
requirements = [
    'beautifulsoup4 >= 4.3.2', # Deal with HTML and XML tags.
#    'lxml >= 3.7.2', # Indirectly used, this is beautifulsoup4's dependency
    'XlsxWriter >= 0.7.3', # Write the XLSX output file.
    'future', # For print statements.
    'tqdm >= 4.30.0', # Progress bar.
    'requests >= 2.18.4', # Scrape, API and web modules.
    'CurrencyConverter >= 0.13', # Used to convert price to a not available currency in one distributor.
    'babel >= 2.6', # For currency format by the language in the spreadsheet.
    'validators >= 0.18.2', # For validation of datasheet URLs in the spreadsheet.
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
#    data_files=data_files,
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    cmdclass={
        'develop': PostDevelopCommand,
        'install': PostInstallCommand,
    }
)
