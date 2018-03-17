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

On Linux, to install KiCost on python3, use::

    $ pip3 install kicost
