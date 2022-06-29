============
Installation
============

This is a Python package, so you'll need to have Python installed to use it.


Windows without KiCad
---------------------

KiCad has Python, but if you don't have KiCad you can download a Python installer from
`Anaconda <https://www.continuum.io/downloads#windows>`_,
`Active State <https://www.activestate.com/activepython/downloads>`_, or even
`WinPython <http://winpython.github.io/#releases>`_.

Once you have Python, you can install this package by opening a terminal
window and typing the command::

    $ easy_install kicost

Or::

    $ pip install kicost

Windows with KiCad
------------------

1. Open a Power Shell window as administrator.

2. Now you need to first add KiCad binaries to your PATH. For a temporal addition you can use:
::

   prompt> $env:Path += ";C:\Program Files\KiCad\bin"

This assumes you installed KiCad in the default place. For a persistent solution search on internet "How to Add to Windows PATH Environment Variable".

3. Install the `wheel` package. Needed to workaround bugs on the Python included with KiCad:
::

   prompt> pip install wheel

4. Now install KiCost, for the last stable release:
::

   prompt> pip install kicost

If you want to install the current development code you must install `GIT <http://git-scm.com/download/win>`_.
After installing GIT::

   prompt> pip install git+https://github.com/hildogjr/KiCost.git


Linux
-----

If you're using linux, you probably already have Python.

On Linux, for a full install procedure on Python3, use (for Python2, replace ``pip3`` by ``pip`` on each command)::

    $ sudo apt-get install python3-pip # Or ``python-pip`` to install PIP on Python2.
    $ sudo -H pip3 install kicost # Install KiCost from PyPI.

To install the graphical dependence used by KiCost GUI (only needed if KiCad is not installed)::

    $ sudo -H pip3 install wxpython
    or
    $ sudo -H pip3 install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-16.04 wxPython # For Ubuntu 16.04
    $ kicost # Execute KiCost without input arguments to initialize the GUI.

To install the last code version from GitHub, use::

    $ sudo apt-get install git # It's necessary to have Git installed.
    $ sudo -H pip3 install -U git+https://github.com/hildogjr/KiCost.git
