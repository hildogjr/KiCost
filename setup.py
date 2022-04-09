#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools
import os
import re
import kicost
import subprocess

try:
    from setuptools import setup
    from setuptools.command.develop import develop
    from setuptools.command.install import install
except ImportError:
    from distutils.core import setup
    from distutils.core.command.develop import develop
    from distutils.core.command.install import install

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


def post_install_setup():
    # Run the KiCost integration script.
    try:
        import sys
        if sys.platform.startswith("win32"):
            # For Windows it is necessary one additional library (used to create the shortcut).
            print('Installing additional library need for Windows setup...')
            try:
                if sys.version_info < (3, 0):
                    from pip._internal import main as pipmain
                else:
                    from pip import main as pipmain
                pipmain(['install', 'pywin32'])
            except Exception:
                print('Error to install Windows additional Python library. KiCost configuration related to Windows registry may not work.')
        # Run setup: shortcut, BOM module to Eeschema and OS context menu.
        try:
            from .kicost.kicost_config import kicost_setup
            kicost_setup()
        except Exception:
            print('Running the external configuration command...')
            from subprocess import call
            call(['kicost', '--setup'])
    except Exception:
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
readme = readme.replace('block_diag.png', 'https://raw.githubusercontent.com/hildogjr/KiCost/master/docs/block_diag.png')
readme = readme.replace('gui.png', 'https://raw.githubusercontent.com/hildogjr/KiCost/master/docs/gui.png')
readme = readme.replace('kitspace.png', 'https://raw.githubusercontent.com/hildogjr/KiCost/master/kicost/kitspace.png')
with open(os.path.join('kicost', 'HISTORY.rst')) as history_file:
    history_full = history_file.read()
    try:
        SHOW_LAST_HISTORY = 3
        RE_TITLE_SEPARATOR = r'(.|\n|\r|\_)'
        update_format = (r'(?P<last_history>'
                         r'History\s\-+\s' + RE_TITLE_SEPARATOR +
                         r'*?(' + RE_TITLE_SEPARATOR +
                         r'*?\s{2,}){'+str(SHOW_LAST_HISTORY)+'}'
                         r')')
        history_lastest = re.search(update_format, history_full).group('last_history').strip()
        if history_lastest:
            if SHOW_LAST_HISTORY == 1:
                history_lastest = history_lastest.replace('History\n-------', 'Latest update\n-------------')
            else:
                history_lastest = history_lastest.replace('History\n-------', 'Latest updates\n--------------')
            history = history_lastest + '\n\nAccess https://github.com/hildogjr/KiCost/blob/master/kicost/HISTORY.rst for full development history.'
        else:
            history = history_full
    except Exception:
        history = history_full
        pass

# KiCost Python packages requirements to run-time.
with open('requirements.txt') as f:
    requirements = f.read().splitlines()
# Remove the comments of the line.
for idx, r in enumerate(requirements):
    requirements[idx] = re.findall('^(.*)(!?#.*)*', r)[0][0].strip()
if '' in requirements:
    requirements.remove('')

# KiCost Python packages requirements to debug and tests.
test_requirements = [
    # Put package test requirements here.
]

# Extra files needed by KiCost.
data_files = [
    # ('kicost', ['kicost/kicost.ico']), # Icon to the user guide. Added via `MANIFEST.in`.
]

with open('kicost/version.py', 'rt') as f:
    version_py = f.read()
with open('kicost/version.py', 'wt') as f:
    if 'KICOST_RELEASE' in os.environ:
        res = 'release'
    else:
        try:
            res = subprocess.check_output(['git', 'log', '-1', '--pretty=format:%h-%as']).decode('ascii')
        except (subprocess.CalledProcessError, FileNotFoundError):
            res = 'unknown'
    f.write(re.sub("__build__ = '(.*)'", "__build__ = '{}'".format(res), version_py))
if 'KICOST_FAKE_VERSION' in os.environ:
    kicost.__version__ = os.environ['KICOST_FAKE_VERSION']

setup(
    name='kicost',
    version=kicost.__version__,
    description="Build cost spreadsheet for a KiCad project.",
    long_description=readme + '\n\n' + history,
    # long_description_content_type="text/reStructuredText",
    author=kicost.__author__,
    author_email=kicost.__email__,
    url='https://hildogjr.github.io/KiCost',
    project_urls={
        'Doc': 'https://hildogjr.github.io/KiCost',
        'Git': 'https://github.com/hildogjr/KiCost',
    },
    packages=setuptools.find_packages(),
    entry_points={'console_scripts': ['kicost = kicost.__main__:main']},
    package_dir={'kicost': 'kicost'},
    include_package_data=True,
    package_data={'kicost': ['*.gif', '*.png', '*.txt']},
    # data_files=data_files,
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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
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
