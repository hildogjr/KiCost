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

# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

from pcbnew import * # KiCad Python library.
import os, subprocess#, threading, time

import traceback, wx # For debug.

def debug_dialog(msg, exception=None):
    if exception:
        msg = '\n'.join((msg, str(exception), traceback.format.exc()))
    dlg = wx.MessageDialog(None, msg, '', wx.OK)
    dlg.ShowModal()
    dlg.Destroy()

class kicost_kicadplugin(ActionPlugin):
    def defaults(self):
        self.name = "KiCad"
        self.category = "BOM"
        self.description = "Create a Cost Bill of Materials spreadsheet using price information on web distributos."

    def Run(self):
        bom_file = os.path.splitext(os.path.basename( GetBoard.GetFileName() ))[0] + '.net'
        if not os.path.isfile(bom_file):
            debug_dialog('The file \'{}\' not exist yet. Return to Eeschma and update it.'.format(bom_file))
        try:
            try:
                from kicost.kicost_gui import *
                try:
                    import wx # Check if wxPython is installed.
                except Exception as e:
                    raise ImportError(e)
                kicost_gui(bom_file)
            except ImportError as e:
                subprocess.call(('kicost', '--guide', bom_file))
        except Exception as e:
            debug_dialog('Error trying to run KiCost as plugin or subprocess.', e)
        return True

# Start point.
kicost_kicadplugin().register()
