============
Installation
============

At the command line::

    $ easy_install kicost

Or, if you have virtualenvwrapper installed::

    $ mkvirtualenv kicost
    $ pip install kicost
    
Note that if you install KiCost using ``pip`` on a Windows system running Python 2.7,
using the default option that web scrapes with parallel processes may cause
**MANY** errors. You can avoid this problem by:

* using ``easy_install`` to install KiCost, or
* use the ``-s`` KiCost option to serialize the web scraping.
