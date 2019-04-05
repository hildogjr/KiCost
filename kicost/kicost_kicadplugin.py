# -*- coding: utf-8 -*- 
# MIT license
#
# Copyright (C) 2018 by Hildo Guillardi Junior
# Copyright (C) 2019
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
__author__ = 'Hildo Guillardi Júnior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

# Libraries.

import pcbnew # KiCad Python library.
import os, subprocess#, threading, time

import traceback, wx # For debug.

import sys, threading, time
import wx.aui


################# Functions.

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

class kicost_kicadplugin(pcbnew.ActionPlugin):
    '''KiCad PcbNew action plugin.'''
    def defaults(self):
        self.name = "KiCost"
        self.category = "BOM"
        self.description = "Create a Cost Bill of Materials spreadsheet using price information on web distributos."

    def Run(self):
        BOM_FILEEXTENSION = '.xml'
        SCH_FILEEXTENSION = '.sch'
        bom_file = os.path.splitext( pcbnew.GetBoard().GetFileName() )[0] + BOM_FILEEXTENSION
        if not os.path.isfile(bom_file):
            debug_dialog('The file \'{}\' not exist yet.\nReturn to Eeschma and update/generate it.'.format(bom_file))
        elif bom_file==BOM_FILEEXTENSION:
            debug_dialog('This boad have not BOM associated.')
            bom_file = ''
        sch_file = os.path.splitext(bom_file)[0] + SCH_FILEEXTENSION
        if os.path.getmtime(bom_file) < os.path.getmtime(sch_file):
            debug_dialog('Schematic file more recent than \'{}\'.'.format(bom_file))
        try:
            try:
                from kicost.kicost_gui import *
                kicost_gui(bom_file) # If KiCad and KiCost share the same Python installation.
            except ImportError:
                subprocess.call('python3 -m kicost --guide \'{}\''.format(bom_file), shell=True)
                #os.system('kicost --guide \"{}\"'.format(bom_file)) # If using different Python installation.
                #os.system('eeschema')
                #subprocess.call('eeschema')
        except Exception as e:
            dlg = debug_dialog('Error trying to run KiCost as plugin or subprocess,\n\
                KiCost is not available or accessible.\n\
                Do you want to try to install KiCost?', e, wx.YES_NO)
            if dlg==wx.YES:
                debug_dialog('YES')
                return True
            else:
                return False
        return True


def check_for_button():
    # From Miles McCoo's blog
    # https://kicad.mmccoo.com/2017/03/05/adding-your-own-command-buttons-to-the-pcbnew-gui/
    def find_pcbnew_window():
        windows = wx.GetTopLevelWindows()
        pcbneww = [w for w in windows if "pcbnew" in w.GetTitle().lower()]
        if len(pcbneww) != 1:
            return None
        return pcbneww[0]
    def callback(_):
        plugin.Run()
    import os
    path = os.path.dirname(__file__)
    while not wx.GetApp():
        time.sleep(1)
    bm = wx.Bitmap(path + '/kicost.png', wx.BITMAP_TYPE_ICO)
    button_wx_item_id = 0
    while True:
        time.sleep(1)
        pcbwin = find_pcbnew_window()
        if not pcbwin:
            continue
        top_tb = pcbwin.FindWindowById(pcbnew.ID_H_TOOLBAR)
        if button_wx_item_id == 0 or not top_tb.FindTool(button_wx_item_id):
            top_tb.AddSeparator()
            button_wx_item_id = wx.NewId()
            top_tb.AddTool(button_wx_item_id, "KiCost", bm,
                           "Generate spreadsheet part cost.", wx.ITEM_NORMAL)
            top_tb.Bind(wx.EVT_TOOL, callback, id=button_wx_item_id)
            top_tb.Realize()


################# Entry point.

plugin = kicost_kicadplugin()
plugin.register()
# Add a button the hacky way if plugin button is not supported in pcbnew, unless this is linux.
#if not plugin.pcbnew_icon_support and not sys.platform.startswith('linux'):
#    t = threading.Thread(target=check_for_button)
#    t.daemon = True
#    t.start()
#TODO it is not working the icon gnerator
