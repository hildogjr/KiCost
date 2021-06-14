# -*- coding: utf-8 -*-

# MIT license
#
# Copyright (C) 2018 by Hildo Guillardi Junior
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
    @package
    Generate an XLSX BOM with costs from internet.

    Command line:
    kicost --gui "%I"
    kicost -qwi "%I"
"""

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# Libraries.
from pcbnew import ActionPlugin, GetBoard  # KiCad Python library.
import os
import subprocess

import traceback  # For debug.
import wx


def debug_dialog(msg, exception=None, kind=wx.OK):
    '''Debug dialog.'''
    if exception:
        msg = '\n'.join((msg, str(exception), traceback.format_exc()))
    dlg = wx.MessageDialog(None, msg, '', kind)
    dlg.ShowModal()
    dlg.Destroy()


def install_kicost():
    '''Install KiCost.'''
    import pip
    pip.main(['install', 'kicost'])
    return


class kicost_kicadplugin(ActionPlugin):
    '''KiCad PcbNew action plugin.'''
    def defaults(self):
        self.name = "KiCost"
        self.category = "BOM"
        self.description = "Create a Cost Bill of Materials spreadsheet using price information on web distributors."

    def Run(self):
        BOM_FILEEXTENSION = '.xml'
        bom_file = os.path.splitext(GetBoard().GetFileName())[0] + BOM_FILEEXTENSION
        if not os.path.isfile(bom_file):
            debug_dialog('The file \'{}\' doesn\'t exist yet.\nReturn to Eeschma and update/generate it.'.format(bom_file))
        elif bom_file == BOM_FILEEXTENSION:
            debug_dialog('This board have not BOM associated.')
            bom_file = ''
        try:
            try:
                from kicost.kicost_gui import kicost_gui
                kicost_gui(bom_file)  # If KiCad and KiCost share the same Python installation.
            except ImportError:
                subprocess.call(('kicost', '--guide', bom_file), shell=True)
                # os.system('kicost --guide \"{}\"'.format(bom_file)) # If using different Python installation.
                # os.system('eeschema')
                # subprocess.call('eeschema')
        except Exception as e:
            dlg = debug_dialog('Error trying to run KiCost as plugin or subprocess,\n\
                KiCost is not available or accessible.\n\
                Do you want to try to install KiCost?', e, wx.YES_NO)
            if dlg == wx.YES:
                debug_dialog('YES')
                return True
            else:
                return False
        return True


# Start point.
kicost_kicadplugin().register()
