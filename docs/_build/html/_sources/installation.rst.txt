============
Installation
============

This is a Python package, so you'll need to have Python installed to use it.
If you're using linux, you probably already have Python.
If you're on Windows, you can download a Python installer from
`Anaconda <https://www.continuum.io/downloads#windows>`_ ,
`Active State <https://www.activestate.com/activepython/downloads>`_ , or even
`WinPython <http://winpython.github.io/#releases>`_ .

Once you have Python, you can install this package by opening a terminal
window and typing the command::

    $ easy_install kicost

Or::

    $ pip install kicost
    
Note that if you install KiCost using ``pip`` on a Windows system running Python 2.7,
using the default option that web scrapes with parallel processes may cause
**MANY** errors. You can avoid this problem by:

* using ``easy_install`` to install KiCost, or
* use the ``-s`` KiCost option to serialize the web scraping.

On Linux, for a full install procedure on Python3, use (for Python2, replace ``pip3`` for ``pip`` on each command)::

    $ sudo apt-get install python3-pip # Or ``python-pip`` to install PIP on Python2.
    $ sudo -H pip3 install -U pip # Upgrade the PIP version.
    $ sudo -H pip3 install kicost # Install KiCost from PyPI.

For install the graphical dependence used by KiCost GUI::

    $ sudo -H pip3 install wxpython
    or
    $ sudo -H pip3 install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-16.04 wxPython # For Ubuntu 16.04
    $ kicost # Execute KiCost without input arguments to initialize the GUI.

For install the last code version from GitHub, use::

    $ sudo apt-get install git # It's necessary to have Git installed.
    $ sudo -H pip3 install -U git+https://github.com/xesscorp/KiCost.git
