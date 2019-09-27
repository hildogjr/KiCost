# -*- coding: utf-8 -*- 

# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Júnior
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

from __future__ import print_function

# Author information.
__author__ = 'Hildo Guillardi Júnior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'

from .global_vars import * # Debug, language and default configurations.

# Libraries.
try:
    import wx # wxWidgets for Python.
except ImportError:
    raise wxPythonNotPresent()
import webbrowser # To update informations.
import sys, os, subprocess # To access OS commands and run in the shell.
import threading
import time # To elapse time.
import platform # To check the system platform when open the XLS file.
import tempfile # To create the temporary log file.
from datetime import datetime # To create the log name, when asked to save.
from distutils.version import StrictVersion # To comparative of versions.
import re # Regular expression parser.
import locale, babel # For country location, language and currency presentation.
import requests
#from .wxAnyThread import anythread

# KiCost libraries.
from . import __version__ # Version control by @xesscorp and collaborator.
from .kicost import *  # kicost core functions.
from .distributors import init_distributor_dict
from .distributors.global_vars import distributor_dict
from .edas import eda_dict
from .edas.tools import file_eda_match
if sys.platform.startswith("win32"):
    from .os_windows import reg_enum_keys, reg_get
    if sys.version_info < (3,0):
        from _winreg import HKEY_LOCAL_MACHINE
    else:
        from winreg import HKEY_LOCAL_MACHINE

__all__ = ['kicost_gui', 'kicost_gui_runterminal']


#=================================
# Guide definitions.

# Open file definitions.
FILE_HIST_QTY_DEFAULT = 10
SEP_FILES = '\n' # File separator in the comboBox.
WILDCARD_BOM = "BOM compatible formats (*.xml,*.csv)|*.xml;*.csv|"\
            "KiCad/Altium BOM file (*.xml)|*.xml|" \
            "Proteus/Generic BOM file (*.csv)|*.csv"

# save settings definitions.
CONFIG_FILE = 'KiCost' # Config file for Linux and Windows registry key for KiCost configurations.
GUI_SIZE_ENTRY = 'GUI_size'
GUI_POSITION_ENTRY = 'GUI_position'
GUI_NEWS_MESSAGE_ENTRY = 'GUI_news_message'

# Links displayed.
PAGE_OFFICIAL = 'https://xesscorp.github.io/KiCost/'
PAGE_UPDATE = 'https://pypi.python.org/pypi/kicost' # Page with the last official version.
#https://github.com/xesscorp/KiCost/blob/master/kicost/version.py
PAGE_DEV = 'https://github.com/xesscorp/KiCost/issues/'
PAGE_POWERED_BY = 'https://kitspace.org/'

kicostPath = os.path.dirname(os.path.abspath(__file__)) # Application dir.

#======================================================================
def open_file(filepath):
    '''@brief Open a file with the default application in different OSs.
       @param filepath str() file name.
    '''
    if sys.platform.startswith(PLATFORM_MACOS_STARTS_WITH): # Mac-OS.
        subprocess.call(('open', filepath))
    elif sys.platform.startswith(PLATFORM_WINDOWS_STARTS_WITH): # Windows.
        os.startfile(filepath)
    elif sys.platform.startswith(PLATFORM_LINUX_STARTS_WITH): # Linux.
        subprocess.call(('xdg-open', filepath))
    else:
        print('Not recognized OS. The spreadsheet file will not be automatically opened.')


#======================================================================
class FileDropTarget(wx.FileDropTarget):
    ''' This object implements Drop Target functionality for Files.
        @param Window handle.
    '''
    def __init__(self, obj):
        ''' @brief Constructor.'''
        wx.FileDropTarget.__init__(self)
        self.obj = obj

    def OnDropFiles(self, x, y, filenames):
        #self.obj.SetInsertionPointEnd()
        self.obj.addFile(filenames)
        return True # No error.


#======================================================================
class menuSelection(wx.Menu):
    ''' @brief Menu of the distributor checkbox list. Provide select all, unselect and toggle hotkey.
        @param TextBox handle.
    '''
    def __init__(self, parent):
        ''' @brief Constructor.'''
        super(menuSelection, self).__init__()
        self.list = parent

        mmi = self.Append(wx.NewId(), 'Select &all')
        self.Bind(wx.EVT_MENU, self.selectAll, mmi)

        mmi = self.Append(wx.NewId(), '&Unselect all')
        self.Bind(wx.EVT_MENU, self.unselectAll, mmi)

        mmi = self.Append(wx.NewId(), '&Toggle')
        self.Bind(wx.EVT_MENU, self.toggleAll, mmi)

    def selectAll(self, event):
        ''' @brief Select all distributor that exist.'''
        event.Skip()
        for idx in range(self.list.GetCount()):
            if not self.list.IsChecked(idx):
                self.list.Check(idx)

    def unselectAll(self, event):
        ''' @brief Unselect all distributor that exist.'''
        event.Skip()
        for idx in range(self.list.GetCount()):
            if self.list.IsChecked(idx):
                self.list.Check(idx, False)

    def toggleAll(self, event):
        ''' @brief Toggle all distributor that exist.'''
        event.Skip()
        for idx in range(self.list.GetCount()):
            if self.list.IsChecked(idx):
                self.list.Check(idx, False)
            else:
                self.list.Check(idx)


#======================================================================
class menuMessages(wx.Menu):
    ''' @brief Menu of the messages text. Provide copy and save options.
        @param TextBox handle.
    '''
    def __init__(self, parent):
        ''' @brief Constructor.'''
        super(menuMessages, self).__init__()
        self.parent = parent

        mmi = self.Append(wx.NewId(), '&Purge')
        self.Bind(wx.EVT_MENU, self.purgeMessages, mmi)

        self.AppendSeparator()

        mmi = self.Append(wx.NewId(), '&Copy to clipboard')
        self.Bind(wx.EVT_MENU, self.copyMessages, mmi)

        mmi = self.Append(wx.NewId(), 'Cut to clip&board')
        self.Bind(wx.EVT_MENU, self.cutMessages, mmi)

        mmi = self.Append(wx.NewId(), '&Save')
        self.Bind(wx.EVT_MENU, self.saveMessages, mmi)

        mmi = self.Append(wx.NewId(), 'S&ave and clear')
        self.Bind(wx.EVT_MENU, self.saveClearMessages, mmi)

        mmi = self.Append(wx.NewId(), '&Open externally')
        self.Bind(wx.EVT_MENU, self.openMessages, mmi)

    def copyMessages(self, event):
        ''' @brief Copy the warning/error/log messages to clipboard.'''
        event.Skip()
        clipdata = wx.TextDataObject()
        clipdata.SetText(self.parent.m_textCtrl_messages.GetValue())
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()

    def cutMessages(self, event):
        ''' @brief Cut the warning/error/log messages to clipboard.'''
        event.Skip()
        self.purgeMessages(event)
        self.copyMessages(event)

    def purgeMessages(self, event):
        ''' @brief Clear message box.'''
        event.Skip()
        self.parent.m_textCtrl_messages.Clear()

    def saveMessages(self, event):
        ''' @brief Save the messages as a text "KiCost*.log" file.'''
        event.Skip()
        actualDir = (os.getcwd() if self.parent.m_comboBox_files.GetValue() else \
            os.path.dirname(os.path.abspath(self.parent.m_comboBox_files.GetValue())))
        dlg = wx.FileDialog(
            self.parent, message = "Save log as...",
            defaultDir = actualDir, 
            defaultFile = "KiCost " + datetime.now().strftime('%Y-%m-%d %Hh%Mmin%Ss'),
            wildcard = "Log file (*.log)|*.log",
            style = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT
           )
        dlg.SetFilterIndex(0)
        if dlg.ShowModal() == wx.ID_OK:
            f = open(dlg.GetPath() , 'w')
            f.write(self.parent.m_textCtrl_messages.GetValue())
            f.close()
            wx.MessageBox('The log file as saved.', 'Info', wx.OK | wx.ICON_INFORMATION)
        dlg.Destroy()

    def saveClearMessages(self, event):
        '''@brief Save the messages and clear the log in the guide.'''
        event.Skip()
        self.saveMessages(event)
        self.purgeMessages(event)

    def openMessages(self, event):
        ''' @brief Save the messages in a temporary file and open it in the default text editor before system delete.'''
        event.Skip()
        #TODO - not working on Ubuntu
        with tempfile.NamedTemporaryFile(prefix='KiCost_', suffix='.log', delete=True, mode='w') as temp:
            temp.write(self.parent.m_textCtrl_messages.GetValue())
            open_file(temp.name)
            temp.close()


#======================================================================
from .kicost_gui_wxFormBuilder import formKiCost_raw
class formKiCost(formKiCost_raw):
    ''' @brief Main frame / form of KiCost GUI.'''

    def __init__(self, parent):
        ''' @brief Constructor, code generated by wxFormBuilder tool.'''
        wx.Frame.__init__ (self, parent, id = wx.ID_ANY, title = u"KiCost", pos = wx.DefaultPosition, size = wx.Size(446,351), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL)

        bSizer1 = wx.BoxSizer(wx.VERTICAL)

        self.m_notebook1 = wx.Notebook(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_panel1 = wx.Panel(self.m_notebook1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.m_panel1.SetToolTip(wx.ToolTip(u"Basic controls, BOM selection and supported distributors."))

        bSizer3 = wx.BoxSizer(wx.VERTICAL)

        sbSizer = wx.StaticBoxSizer(wx.StaticBox(self.m_panel1, wx.ID_ANY, u"BOM input files:"), wx.HORIZONTAL)
        m_comboBox_filesChoices = []
        self.m_comboBox_files = wx.ComboBox(sbSizer.GetStaticBox(), wx.ID_ANY, u"Not selected files", wx.DefaultPosition, wx.DefaultSize, m_comboBox_filesChoices, 0)
        self.m_comboBox_files.SetToolTip(wx.ToolTip(u"BOM(s) file(s) to scrape.\nClick on the arrow to see/select one of the history files."))
        sbSizer.Add(self.m_comboBox_files, 1, wx.ALL, 5)
        self.m_comboBox_files.Bind(wx.EVT_COMBOBOX, self.m_comboBox_files_selecthist)
        self.m_button_openfile = wx.Button(sbSizer.GetStaticBox(), wx.ID_ANY, u"Choose BOM", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_button_openfile.SetToolTip(wx.ToolTip(u"Click to choose the BOM(s) file(s)."))
        self.m_button_openfile.Bind(wx.EVT_BUTTON, self.button_openfile)
        sbSizer.Add(self.m_button_openfile, 0, wx.ALL, 5)
        bSizer3.Add(sbSizer, 0, wx.EXPAND|wx.TOP, 5)

        sbSizer = wx.StaticBoxSizer(wx.StaticBox(self.m_panel1, wx.ID_ANY, u"Spreadsheet output file:"), wx.HORIZONTAL)
        self.m_text_saveas = wx.TextCtrl(sbSizer.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.TE_NOHIDESEL)
        self.m_text_saveas.SetToolTip(wx.ToolTip(u"Output spreadsheet file name."))
        sbSizer.Add(self.m_text_saveas, 1, wx.ALL, 5)
        self.m_button_saveas = wx.Button(sbSizer.GetStaticBox(), wx.ID_ANY, u"Save as...", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_button_saveas.SetToolTip(wx.ToolTip(u"Click to change the output spreadsheet file name."))
        self.m_button_saveas.Bind(wx.EVT_BUTTON, self.button_saveas)
        sbSizer.Add(self.m_button_saveas, 0, wx.ALL, 5)
        bSizer3.Add(sbSizer, 0, wx.EXPAND|wx.TOP, 5)

        bSizer4 = wx.BoxSizer(wx.HORIZONTAL)

        sbSizer3 = wx.StaticBoxSizer(wx.StaticBox(self.m_panel1, wx.ID_ANY, u"Distributors to get price:"), wx.VERTICAL)
        m_checkList_distChoices = [wx.EmptyString]
        self.m_checkList_dist = wx.CheckListBox(sbSizer3.GetStaticBox(), wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, m_checkList_distChoices, 0)
        self.m_checkList_dist.SetToolTip(wx.ToolTip(u"Select the web distributor (or local) that will be used to scrape the prices.\nClick right to hot option."))
        sbSizer3.Add(self.m_checkList_dist, 1, wx.ALL|wx.EXPAND, 5)
        self.m_checkList_dist.Bind(wx.EVT_RIGHT_DOWN, self.m_textCtrl_distributors_rClick)
        bSizer4.Add(sbSizer3, 1, wx.EXPAND|wx.TOP|wx.LEFT, 5)

        wSizer1 = wx.WrapSizer(wx.VERTICAL)

        bSizer6 = wx.BoxSizer(wx.VERTICAL)

        sbSizer31 = wx.StaticBoxSizer(wx.StaticBox(self.m_panel1, wx.ID_ANY, u"Recognized EDAs:"), wx.VERTICAL)
        m_listBox_edatoolChoices = []
        self.m_listBox_edatool = wx.ListBox(sbSizer31.GetStaticBox(), wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, m_listBox_edatoolChoices, 0)
        self.m_listBox_edatool.SetToolTip(wx.ToolTip(u"Choose the correct EDA software corresponding to the BOM file.\nCSVs files are used by the most of commercial software and to make the hand made BOM."))
        sbSizer31.Add(self.m_listBox_edatool, 1, wx.ALL|wx.EXPAND, 5)
        bSizer6.Add(sbSizer31, 1, wx.TOP|wx.RIGHT|wx.EXPAND, 5)

        # Allow convert to XLSX to ODS quietly because this load more smoothly on LibreOffice.
        self.m_checkBox_XLSXtoODS = wx.CheckBox(self.m_panel1, wx.ID_ANY, u"Convert to ODS", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_checkBox_XLSXtoODS.SetValue(False)
        self.m_checkBox_XLSXtoODS.SetToolTip(wx.ToolTip(u"Convert the file output to ODS format quietly."))
        self.m_checkBox_XLSXtoODS.Bind(wx.EVT_CHECKBOX, self.updateOutputFilename)
        bSizer6.Add(self.m_checkBox_XLSXtoODS, 0, wx.ALL, 5)
        # LibreOffice identification
        if sys.platform.startswith("win32"):
            try:
                libreoffice_reg = r'SOFTWARE\LibreOffice\LibreOffice'
                libreoffice_installations = reg_enum_keys(libreoffice_reg, HKEY_LOCAL_MACHINE)
                logger.log(DEBUG_OVERVIEW, 'Found LibreOffice {} installation(s) version(s).'.format(libreoffice_installations))
                libreoffice_installations.sort(key=StrictVersion)
                libreoffice_executable = reg_get(
                        os.path.join(libreoffice_reg, os.path.join(libreoffice_reg, libreoffice_installations[-1]), 'Path'),
                        HKEY_LOCAL_MACHINE)
                logger.log(DEBUG_OVERVIEW, 'Last LibreOffice installation at {}.'.format(libreoffice_executable))
            except:
                logger.log(DEBUG_OVERVIEW, 'LibreOffice not found.')
                libreoffice_executable = None
        else:
            from distutils.spawn import find_executable
            libreoffice_executable = find_executable('libreoffice')
        # Create a control to convert the XLSX to ODS quietly.
        if libreoffice_executable:
            self.m_checkBox_XLSXtoODS.Enable() # Recognized LibreOffice.
        else:
            logger.log(DEBUG_OBSESSIVE, 'LibreOffice not found.')
            self.m_checkBox_XLSXtoODS.SetValue(False)

        self.m_checkBox_openSpreadsheet = wx.CheckBox(self.m_panel1, wx.ID_ANY, u"Open spreadsheet", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_checkBox_openSpreadsheet.SetValue(True)
        self.m_checkBox_openSpreadsheet.SetToolTip(wx.ToolTip(u"Open the spreadsheet after finish the KiCost scrape."))
        bSizer6.Add(self.m_checkBox_openSpreadsheet, 0, wx.ALL, 5)

        self.m_button_run = wx.Button(self.m_panel1, wx.ID_ANY, u"KiCost it!", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_button_run.SetToolTip(wx.ToolTip(u"Click to run KiCost."))
        self.m_button_run.Bind(wx.EVT_BUTTON, self.button_run)
        bSizer6.Add(self.m_button_run, 0, wx.ALL, 5)

        wSizer1.Add(bSizer6, 1, wx.RIGHT|wx.EXPAND, 5)

        bSizer4.Add(wSizer1, 1, wx.EXPAND, 5)

        bSizer3.Add(bSizer4, 1, wx.EXPAND, 5)

        fgSizer1 = wx.FlexGridSizer(0, 4, 0, 0)
        fgSizer1.SetFlexibleDirection(wx.BOTH)
        fgSizer1.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

        self.m_gauge_process = wx.Gauge(self.m_panel1, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL)
        self.m_gauge_process.SetValue(0) 
        self.m_gauge_process.SetToolTip(wx.ToolTip(u"Percentage of the scrape process elapsed."))
        fgSizer1.Add(self.m_gauge_process, 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.m_staticText_progressInfo = wx.StaticText(self.m_panel1, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.ALIGN_RIGHT)
        self.m_staticText_progressInfo.Wrap(-1)
        self.m_staticText_progressInfo.SetToolTip(wx.ToolTip(u"Progress information."))

        fgSizer1.Add(self.m_staticText_progressInfo, 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, 5)

        bSizer3.Add(fgSizer1, 0, wx.EXPAND, 5)

        m_staticText = wx.StaticText(self.m_panel1, wx.ID_ANY, u"Warnings, debug and error messages:", wx.DefaultPosition, wx.DefaultSize, 0)
        m_staticText.Wrap(-1)
        bSizer3.Add(m_staticText, 0, wx.ALL|wx.EXPAND, 5)
        self.m_textCtrl_messages = wx.TextCtrl(self.m_panel1, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(-1,4), wx.HSCROLL|wx.TE_MULTILINE|wx.TE_READONLY)
        self.m_textCtrl_messages.SetToolTip(wx.ToolTip(u"Process messages and warnings.\nClick right to copy or save the log."))
        self.m_textCtrl_messages.SetMinSize(wx.Size(-1,4))
        self.m_textCtrl_messages.Bind(wx.EVT_RIGHT_DOWN, self.m_textCtrl_messages_rClick)
        bSizer3.Add(self.m_textCtrl_messages, 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 5)

        ## Configuration tab.
        self.m_panel1.SetSizer(bSizer3)
        self.m_panel1.Layout()
        bSizer3.Fit(self.m_panel1)
        self.m_notebook1.AddPage(self.m_panel1, u"Cost BOM creation", False)
        self.m_panel2 = wx.Panel(self.m_notebook1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.m_panel2.SetToolTip(wx.ToolTip(u"KiCost general configurations tab."))

        bSizer8 = wx.BoxSizer(wx.VERTICAL)

        wSizer2 = wx.WrapSizer(wx.HORIZONTAL)

        bSizer9 = wx.BoxSizer(wx.VERTICAL)

        m_staticText = wx.StaticText(self.m_panel2, wx.ID_ANY, u"Spreadsheet currency:", wx.DefaultPosition, wx.DefaultSize, 0)
        m_staticText.Wrap(-1)
        bSizer9.Add(m_staticText, 0, wx.ALL, 5)
        self.m_comboBox_currency = wx.ComboBox(self.m_panel2, wx.ID_ANY, u"", wx.DefaultPosition, wx.DefaultSize, [], 0)
        self.m_comboBox_currency.SetToolTip(wx.ToolTip(u"Currency to be used to generate the Cost Bill of Materials.\nIn case of not available the current distributor (API/Scrape/...) is converted to and distributor column receive a comment."))
        bSizer9.Add(self.m_comboBox_currency, 0, wx.ALL, 5)

        wSizer2.Add(bSizer9, 1, wx.TOP|wx.LEFT, 5)

        bSizer11 = wx.BoxSizer(wx.VERTICAL)

        self.m_checkBox_collapseRefs = wx.CheckBox(self.m_panel2, wx.ID_ANY, u"Collapse refs", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_checkBox_collapseRefs.SetValue(True) 
        self.m_checkBox_collapseRefs.SetToolTip(wx.ToolTip(u"Collapse the references in the spreadsheet.\n'R1,R2,R3,R4,R9' become 'R1-R4,R9' with checked."))
        bSizer11.Add(self.m_checkBox_collapseRefs, 0, wx.ALL, 5)

        m_staticText = wx.StaticText(self.m_panel2, wx.ID_ANY, u"Debug level:", wx.DefaultPosition, wx.DefaultSize, 0)
        m_staticText.Wrap(-1)
        bSizer11.Add(m_staticText, 0, wx.ALL, 5)
        self.m_spinCtrl_debugLvl = wx.SpinCtrl(self.m_panel2, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 0, 10, 0)
        bSizer11.Add(self.m_spinCtrl_debugLvl, 0, wx.ALL, 5)

        self.m_checkBox_quite = wx.CheckBox(self.m_panel2, wx.ID_ANY, u"Quiet mode", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_checkBox_quite.SetToolTip(wx.ToolTip(u"Enable quiet mode with no warnings or messages at all."))
        bSizer11.Add(self.m_checkBox_quite, 0, wx.ALL, 5)

        self.m_checkBox_overwrite = wx.CheckBox(self.m_panel2, wx.ID_ANY, u"Overwrite file", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_checkBox_overwrite.SetValue(True) 
        self.m_checkBox_overwrite.SetToolTip(wx.ToolTip(u"Allow overwriting of an existing spreadsheet."))
        bSizer11.Add(self.m_checkBox_overwrite, 0, wx.ALL, 5)


        m_staticText = wx.StaticText(self.m_panel2, wx.ID_ANY, u"History keep:", wx.DefaultPosition, wx.DefaultSize, 0)
        m_staticText.Wrap(-1)
        bSizer11.Add(m_staticText, 0, wx.ALL, 5)
        self.m_spinCtrl_histotyLen = wx.SpinCtrl(self.m_panel2, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 1, 30, 6)
        self.m_spinCtrl_histotyLen.SetToolTip(wx.ToolTip(u"Quantity of files kept on history."))
        bSizer11.Add(self.m_spinCtrl_histotyLen, 0, wx.ALL, 5)
        self.m_spinCtrl_histotyLen.SetValue(FILE_HIST_QTY_DEFAULT)

        m_staticText = wx.StaticText(self.m_panel2, wx.ID_ANY, u"GUI language:", wx.DefaultPosition, wx.DefaultSize, 0)
        m_staticText.Wrap(-1)
        bSizer11.Add(m_staticText, 0, wx.ALL, 5)
        self.m_comboBox_language = wx.ComboBox(self.m_panel2, wx.ID_ANY, u"", wx.DefaultPosition, wx.DefaultSize, [], 0)
        self.m_comboBox_language.SetToolTip(wx.ToolTip(u"Setup the guide language (needs restart)."))
        bSizer11.Add(self.m_comboBox_language, 0, wx.ALL, 5)

        wSizer2.Add(bSizer11, 1, wx.TOP|wx.RIGHT, 5)

        bSizer8.Add(wSizer2, 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 5)

        m_staticText = wx.StaticText(self.m_panel2, wx.ID_ANY, u"Extra commands:", wx.DefaultPosition, wx.DefaultSize, 0)
        m_staticText.Wrap(-1)
        bSizer8.Add(m_staticText, 0, wx.ALL, 5)
        self.m_textCtrl_extraCmd = wx.TextCtrl(self.m_panel2, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_textCtrl_extraCmd.SetToolTip(wx.ToolTip(u"Here use the KiCost extra commands. In the terminal/command type`kicost --help` to check the list.\nThe command here take priority over the other guide control."))

        bSizer8.Add(self.m_textCtrl_extraCmd, 0, wx.ALL|wx.EXPAND, 5)

        self.m_panel2.SetSizer(bSizer8)
        self.m_panel2.Layout()
        bSizer8.Fit(self.m_panel2)
        self.m_notebook1.AddPage(self.m_panel2, u"Configurations", False)
        self.m_panel3 = wx.Panel(self.m_notebook1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.m_panel3.SetToolTip(wx.ToolTip(u"About the software, version installation and update found."))

        bSizer2 = wx.BoxSizer(wx.VERTICAL)

        bSizer10 = wx.BoxSizer(wx.HORIZONTAL)

        bSizer101 = wx.BoxSizer(wx.VERTICAL)

        self.m_bitmap_icon = wx.StaticBitmap(self.m_panel3, wx.ID_ANY, wx.NullBitmap, wx.DefaultPosition, wx.Size(200,100),0)#wx.DefaultSize, 0)
        self.m_bitmap_icon.SetIcon(wx.Icon(os.path.join(kicostPath, 'kicost.ico'), wx.BITMAP_TYPE_ICO))
        bSizer101.Add(self.m_bitmap_icon, 0, wx.CENTER | wx.ALL, 5)

        self.m_staticText_version = wx.StaticText(self.m_panel3, wx.ID_ANY, u"version", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_staticText_version.Wrap(-1)
        self.m_staticText_version.SetLabel('Version ' + __version__)
        bSizer101.Add(self.m_staticText_version, 1, wx.ALL, 5)

        self.m_button_open_webpage = wx.Button(self.m_panel3, wx.ID_ANY, u"Online manual", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_button_open_webpage.SetToolTip(wx.ToolTip(u"Click for official web page user manual."))
        self.m_button_open_webpage.Bind(wx.EVT_LEFT_DOWN, self.open_webpage_click)
        bSizer101.Add(self.m_button_open_webpage, 0, wx.CENTER | wx.ALL, 5)

        self.m_button_open_issuepage = wx.Button(self.m_panel3, wx.ID_ANY, u"Report issue page", \
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_button_open_issuepage.SetToolTip(wx.ToolTip(u"Open KiCost project ISSUE report page on GitHub."))
        bSizer101.Add(self.m_button_open_issuepage, 0, wx.CENTER | wx.ALL, 5)
        self.m_button_open_issuepage.Bind(wx.EVT_LEFT_DOWN, self.open_issuepage_click)

        bSizer111 = wx.BoxSizer(wx.VERTICAL)

        self.m_bitmap_icon = wx.StaticBitmap(self.m_panel3, wx.ID_ANY, wx.NullBitmap, wx.DefaultPosition, wx.Size(200,100),0)#wx.DefaultSize, 0)
        self.m_bitmap_icon.SetIcon(wx.Icon(os.path.join(kicostPath,'kitspace.png'), wx.BITMAP_TYPE_PNG))
        self.m_bitmap_icon.Bind(wx.EVT_LEFT_DOWN, self.open_powered_by)
        bSizer111.Add(self.m_bitmap_icon, 0, wx.CENTER | wx.ALL, 5)

        self.m_button_check_updates = wx.Button(self.m_panel3, wx.ID_ANY, u"Check for updates", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_button_check_updates.SetToolTip(wx.ToolTip(u"Click for compare you version with the most recent released."))
        self.m_button_check_updates.Bind(wx.EVT_BUTTON, self.check_updates_click)
        bSizer111.Add(self.m_button_check_updates, 0, wx.CENTER | wx.ALL, 5)

        self.m_button_open_updatepage = wx.Button(self.m_panel3, wx.ID_ANY, u"Open PyPI page", \
            wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_button_open_updatepage.SetToolTip(wx.ToolTip(u"Open PyPI page with the most recent KiCost version."))
        self.m_button_open_updatepage.Bind(wx.EVT_LEFT_DOWN, self.open_updatepage_click)
        bSizer111.Add(self.m_button_open_updatepage, 0,  wx.CENTER | wx.ALL, 5)

        bSizer10.Add(bSizer101, 1, wx.EXPAND, 5)
        bSizer10.Add(bSizer111, 1, wx.EXPAND, 5)

        bSizer2.Add(bSizer10, 0, wx.ALL|wx.EXPAND, 5)

        self.m_text_credits = wx.TextCtrl(self.m_panel3, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(-1,4), wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_AUTO_URL|wx.TE_BESTWRAP)
        bSizer2.Add(self.m_text_credits, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 5)
        self.m_text_credits.SetValue('jkjtke')

        self.m_panel3.SetSizer(bSizer2)
        self.m_panel3.Layout()
        bSizer2.Fit(self.m_panel3)
        self.m_notebook1.AddPage(self.m_panel3, u"About", True)

        bSizer1.Add(self.m_notebook1, 1, wx.EXPAND |wx.ALL, 5)

        self.SetSizer(bSizer1)
        self.Layout()
        self.Centre(wx.BOTH)
        self.Bind(wx.EVT_CLOSE, self.app_close)
        self.Fit() # Set the window size to fit all controls, useful in first
                   # execution without the last size and position saved.
        #self.SetSizeHints(wx.Size(40, 40), wx.DefaultSize) # Only available on wxPython4.



        # Set the application windows title and configurations.
        self.SetTitle('KiCost v.' + __version__)
        self.SetIcon(wx.Icon(os.path.join(kicostPath, 'kicost.ico'), wx.BITMAP_TYPE_ICO))

        self.set_properties()
        self.SetDropTarget(FileDropTarget(self)) # Start the drop file in all the window.
        logger.log(DEBUG_OVERVIEW, 'Loaded KiCost v.' + __version__)

    def __del__(self):
        pass

    # Virtual event handlers, overwrite them in your derived class

    #----------------------------------------------------------------------
    def app_close(self, event):
        ''' @brief Close event, used to call the save settings.'''
        event.Skip()
        self.save_properties()

    #----------------------------------------------------------------------
    '''About page, report and official informations.'''
    def open_webpage_click(self, event):
        ''' @brief Open the official software web page in the default browser.'''
        event.Skip()
        webbrowser.open(PAGE_OFFICIAL)
    def open_issuepage_click(self, event):
        ''' @brief Open the official software web page in the default browser.'''
        event.Skip()
        webbrowser.open(PAGE_DEV)
    def open_updatepage_click(self, event):
        ''' @brief Open the page to download the last version.'''
        event.Skip()
        webbrowser.open(PAGE_UPDATE)
    def open_powered_by(self, event):
        ''' @brief Open partner that power the KiCost.'''
        event.Skip()
        webbrowser.open(PAGE_POWERED_BY)

    #----------------------------------------------------------------------
    def check_updates_click(self, event):
        ''' @brief Check version to update if the "About" tab.'''
        event.Skip()
        def checkUpdate():
            '''Check for updates.'''
            self.m_button_check_updates.SetLabel(u"Checking for updates...")
            try:
                response = requests.get(PAGE_UPDATE)
                html = response.text
                offical_last_version = re.findall('kicost (\d+\.\d+\.\d+)', str(html), flags=re.IGNORECASE)[0]
                if StrictVersion(offical_last_version) > StrictVersion(__version__):
                    self.m_button_check_updates.SetLabel(u"Found v{}.".format(offical_last_version) )
                    #self.m_staticText_update.Bind(wx.EVT_LEFT_UP, self.m_staticText_update_click)
                else:
                    self.m_button_check_updates.SetLabel(u"KiCost is up to date")
            except:
                self.m_button_check_updates.SetLabel(u"No information")
        wx.CallLater(50, checkUpdate) # Thread optimized for graphical elements change.

    #----------------------------------------------------------------------
    '''Pop-up menus on main tab.'''
    def m_textCtrl_messages_rClick(self, event):
        ''' @brief Open the context menu with save log options.'''
        event.Skip()
        self.PopupMenu(menuMessages(self), event.GetPosition())
    def m_textCtrl_distributors_rClick(self, event):
        ''' @brief Open the context menu with distributors options.'''
        event.Skip()
        self.PopupMenu(menuSelection(self.m_checkList_dist), event.GetPosition())

    #----------------------------------------------------------------------
    def m_comboBox_files_selecthist(self, event):
        ''' @brief Update the select EDA module tool when changed the file selected in the history, update the order and delete if file not existent.'''
        event.Skip()
        # Check if the file in the file name exist and
        # update the history sequence, if don't, remove it.
        histSelected = event.GetSelection()
        fileNames = event.GetString()
        self.m_comboBox_files.Delete(histSelected)
        if all(os.path.isfile(f) for f in re.split(SEP_FILES, fileNames)):
            self.m_comboBox_files.Insert(fileNames, 0)
            self.updateEDAselection() # Auto-select the EDA module.
            self.updateOutputFilename() # Update the output file name on GUI text.
        else:
            self.m_comboBox_files.SetValue('')

    #----------------------------------------------------------------------
    def updateOutputFilename(self, event=None):
        ''' @brief Update the output file name on the GUI.'''
        spreadsheet_file = output_filename( re.split(SEP_FILES, self.m_comboBox_files.GetValue()) )
        if self.m_checkBox_XLSXtoODS.GetValue():
            spreadsheet_file = os.path.splitext(spreadsheet_file)[0] + '.ods'
        self.m_text_saveas.SetValue(spreadsheet_file)

    #----------------------------------------------------------------------
    def updateEDAselection(self):
        ''' @brief Update the EDA selection in the listBox based on the comboBox actual text.'''
        fileNames = re.split(SEP_FILES, self.m_comboBox_files.GetValue())
        if len(fileNames)==1:
            eda_module = file_eda_match(fileNames[0])
            if eda_module:
                self.m_listBox_edatool.SetSelection(self.m_listBox_edatool.FindString(eda_dict[eda_module]['label']))
        elif len(fileNames)>1:
            # Check if all the EDA are the same. For different ones,
            # the guide is not able now to deal, need improvement
            # on `self.m_listBox_edatool`.
            eda_module = file_eda_match(fileNames[0])
            for fName in fileNames[1:]:
                if file_eda_match(fName) != eda_module:
                    return
            if eda_module:
                self.m_listBox_edatool.SetSelection(self.m_listBox_edatool.FindString(eda_dict[eda_module]['label']))

    #----------------------------------------------------------------------
    def button_openfile(self, event):
        """ @brief Create and show the Open FileDialog"""
        event.Skip()
        actualDir = (os.getcwd() if self.m_comboBox_files.GetValue() else \
            os.path.dirname(os.path.abspath(self.m_comboBox_files.GetValue())))
        dlg = wx.FileDialog(self, message = "Select BOM(s)", defaultDir = actualDir, 
            defaultFile = "", wildcard = WILDCARD_BOM,
            style = wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            self.addFile(dlg.GetPaths())
            self.updateOutputFilename() # Update the output file name on GUI text.
        dlg.Destroy()

    #----------------------------------------------------------------------
    def button_saveas(self, event):
        """ @brief Create and show the Save As... FileDialog."""
        event.Skip()
        wildcard = ("Open format (*.ods)|*.ods" if self.m_checkBox_XLSXtoODS.GetValue()\
            else "Microsoft Excel (*.xlsx)|*.xlsx")
        actualFile = (os.getcwd() if self.m_text_saveas.GetValue() else \
            os.path.dirname(os.path.abspath(self.m_text_saveas.GetValue())))
        dlg = wx.FileDialog(self, message = "Save spreadsheet as...", defaultDir = actualFile, 
            defaultFile = "", wildcard = wildcard,
            style = wx.FD_SAVE | wx.FD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            spreadsheet_file = dlg.GetPaths()[0]
            if not re.search('^.(xlsx|odt)$', os.path.splitext(spreadsheet_file)[1], re.IGNORECASE):
                spreadsheet_file += ('.ods' if self.m_checkBox_XLSXtoODS.GetValue() else '.xlsx')
            self.m_text_saveas.SetValue(spreadsheet_file)
        dlg.Destroy()

    #----------------------------------------------------------------------
    def addFile(self, filesName):
        ''' @brief Add the file(s) to the history, updating it (and delete the too old).'''
        if sys.version_info >= (3,0):
            sorted_files = sorted(filesName, key=str.lower)
        else:
            sorted_files = sorted(filesName, key=unicode.lower)
        fileBOM = SEP_FILES.join(sorted_files) # Add the files sorted.
        if self.m_comboBox_files.FindString(fileBOM)==wx.NOT_FOUND:
            self.m_comboBox_files.Insert(fileBOM, 0)
        self.m_comboBox_files.SetValue(fileBOM)
        try:
            self.m_comboBox_files.Delete(self.m_spinCtrl_histotyLen.GetValue()-1) # Keep 10 files on history.
        except:
            pass
        self.updateEDAselection()

    #----------------------------------------------------------------------
    def button_run(self, event):
        ''' @brief Call to run KiCost.'''
        event.Skip()
        #self.run()
        #wx.CallLater(10, self.run) # Necessary to not '(core dumped)' with wxPython.
        t = threading.Thread(target=self.run)#, args=[self])
        t.start()

    #----------------------------------------------------------------------
    #@anythread
    def run(self):
        ''' @brief Run KiCost.
            Run KiCost in the GUI interface updating the process bar and messages.'''

        self.m_gauge_process.SetValue(0)
        self.m_button_run.Disable()
        self.save_properties() # Save the current graphical configuration before call the KiCost.

        class argments:
            pass
        args = argments()

        args.input = re.split(SEP_FILES, self.m_comboBox_files.GetValue())
        for f in args.input:
            if not os.path.isfile(f):
                print('No valid file(s) selected.')
                self.m_button_run.Enable()
                return # Not a valid file(s).

        spreadsheet_file = self.m_text_saveas.GetValue()
        # Handle case where output is going into an existing spreadsheet file.
        if os.path.isfile(spreadsheet_file):
            if not self.m_checkBox_overwrite.GetValue():
                dlg = wx.MessageDialog(self, 
                    "The file output \'{}\' already exit, do you want overwrite?".format(
                                os.path.basename(spreadsheet_file)
                           ),
                    "Confirm Overwrite", wx.YES_NO|wx.YES_DEFAULT|wx.ICON_QUESTION|wx.STAY_ON_TOP|wx.CENTER)
                result = dlg.ShowModal()
                dlg.Destroy()
                if result==wx.ID_NO:
                    print('Not able to overwrite \'{}\'...'.format(
                                os.path.basename(spreadsheet_file)
                           )
                       )
                    return
        spreadsheet_file = os.path.splitext(spreadsheet_file)[0] + '.xlsx' # Force the output (for the CLI interface) to be .XLSX.
        args.output = spreadsheet_file

        if self.m_textCtrl_extraCmd.GetValue():
            extra_commands = ' ' + self.m_textCtrl_extraCmd.GetValue()
        else:
            extra_commands = []

        def str_to_arg(commands):
            try:
                for c in commands:
                    try:
                        return ''.join(re.findall(c+' (.+)', extra_commands))
                    except:
                        continue
            except:
                pass
            finally:
                return ''
        args.fields = str_to_arg(['--fields', '-f']).split()
        args.ignore_fields = str_to_arg(['--ignore_fields', '-ign']).split()
        args.group_fields = str_to_arg(['--group_fields', '-grp']).split()
        args.translate_fields = str_to_arg(['--translate_fields']).split()
        args.variant = str_to_arg(['--variant', '-var'])
        try:
            args.currency = re.findall('\((\w{3}) .*\).*', self.m_comboBox_currency.GetValue())[0]
        except IndexError:
            pass # Doesn't work under Python 2 so I'm just ignoring it.

        args.collapse_refs = self.m_checkBox_collapseRefs.GetValue() # Collapse refs in the spreadsheet.

        if self.m_listBox_edatool.GetStringSelection():
            for k,v in eda_dict.items():
               if v['label']==self.m_listBox_edatool.GetStringSelection():
                  args.eda_name = v['module'] # The selected EDA module on GUI.
                  break

        # Get the current distributors to scrape.
        #choisen_dist = list(self.m_checkList_dist.GetCheckedItems()) # Only valid on wxPy4.
        choisen_dist = [i for i in range(self.m_checkList_dist.GetCount()) if self.m_checkList_dist.IsChecked(i)]
        if choisen_dist:
            dist_list = []
            #choisen_dist = [self.m_checkList_dist.GetString(idx) for idx in choisen_dist]
            for idx in choisen_dist:
                label = self.m_checkList_dist.GetString(idx)
                for k,v in distributor_dict.items():
                    if v['label']['name']==label:
                        dist_list.append(k)
                        break
        else:
            dist_list = None
        args.include = dist_list

        # Run KiCost main function and print in the log the elapsed time.
        start_time = time.time()
        try:
            #print(args.input, '\n', args.eda_name, '\n', args.output, '\n', args.collapse_refs,
            #    '\n', args.fields, '\n', args.ignore_fields, '\n', args.include, '\n', args.currency)
            kicost(in_file=args.input, eda_name=args.eda_name,
                out_filename=args.output, collapse_refs=args.collapse_refs,
                user_fields=args.fields, ignore_fields=args.ignore_fields,
                group_fields=args.group_fields, translate_fields=args.translate_fields,
                variant=args.variant,
                dist_list=args.include, currency=args.currency)
        except Exception as e:
            logger.log(DEBUG_OVERVIEW, e)
            self.m_button_run.Enable()
            return
        finally:
            init_distributor_dict() # Restore distributors removed during the execution of KiCost motor.
        logger.log(DEBUG_OVERVIEW, 'Elapsed time: {} seconds'.format(time.time() - start_time))
        try:
            if self.m_checkBox_XLSXtoODS.GetValue():
                logger.log(DEBUG_OVERVIEW, 'Converting \'{}\' to ODS file...'.format(
                                    os.path.basename(spreadsheet_file) ) )
                os.system('{e} --headless --convert-to ods {i} --outdir {o}'.format(e=libreoffice_executable, si=spreadsheet_file, o=os.path.dirname(spreadsheet_file)))
                #os.remove(spreadsheet_file) # Delete the older file.
                spreadsheet_file = os.path.splitext(spreadsheet_file)[0] + '.ods'
        except Exception as e:
            logger.log(DEBUG_OVERVIEW, '\'{}\' could be not converted to ODS: {}'.format(os.path.basename(spreadsheet_file), e) )
            pass
        try:
            if self.m_checkBox_openSpreadsheet.GetValue():
                logger.log(DEBUG_OVERVIEW, 'Opening the output file \'{}\'...'.format(
                                    os.path.basename(spreadsheet_file) ) )
                open_file(spreadsheet_file)
        except Exception as e:
            logger.log(DEBUG_OVERVIEW, '\'{}\' could be not opened: {}'.format(os.path.basename(spreadsheet_file), e) )

        self.m_gauge_process.SetValue(100)
        self.m_button_run.Enable()
        return

    #----------------------------------------------------------------------
    def set_properties(self):
        ''' @brief Set the current proprieties of the graphical elements.'''

        # Current distributors module recognized.
        distributors_list = sorted([ distributor_dict[d]['label']['name'] for d in distributor_dict.keys() if distributor_dict[d]['type']!='local'])
        self.m_checkList_dist.Clear()
        for d in distributors_list: # Make this for wxPy3 compatibility, not allow include a list.
            self.m_checkList_dist.Append(d)
        #self.m_checkList_dist.Append(distributors_list)
        for idx in range(len(distributors_list)):
            self.m_checkList_dist.Check(idx,True) # All start checked (after is modified by the configuration file).

        # Current EDA tools module recognized.
        eda_names = sorted([ eda_dict[eda]['label'] for eda in eda_dict.keys() ])
        self.m_listBox_edatool.Clear()
        for s in eda_names: # Make this for wxPy3 compatibility, not allow include a list.
            self.m_listBox_edatool.Append(s)
        #self.m_listBox_edatool.Append(eda_names)

        # Get all the currencies present.
        loc = locale.getdefaultlocale()[0]
        currencyList = sorted(list(babel.numbers.list_currencies()))
        for c in range(len(currencyList)):
            currency = currencyList[c]
            currencyList[c] = '({a} {s}) {n}'.format(a=currency,
                                                  s=babel.numbers.get_currency_symbol(currency, locale=loc),
                                                  n=babel.numbers.get_currency_name(currency, locale=loc)
                                              )
        self.m_comboBox_currency.Insert(currencyList, 0)

        # Get all languages possible.
        languages = '{n} ({s})'.format(n=babel.Locale(DEFAULT_LANGUAGE).get_language_name(),
                                      s=DEFAULT_LANGUAGE,
                                  )
        self.m_comboBox_language.Insert(languages, 0)

        # Credits and other informations, search by `AUTHOR.rst` file.
        try:
            credits_file = open(os.path.join(kicostPath, 'AUTHORS.rst') )
            credits = credits_file.read()
            credits_file.close()
        except:
            credits = r'''=======
            Credits
            =======
            Development Lead:
            * XESS Corporation <info@xess.com>
            ------------
            GUI, main collaborator and maintainer:
            * Hildo Guillardi Júnior https://github.com/hildogjr
            ------------
            Contributors:
            See https://github.com/xesscorp/KiCost/ for the full list.
            '''
            credits = re.sub(r'\n[\t ]+', '\n', credits)  # Remove leading whitespace
        self.m_text_credits.SetValue(credits)

        # Recovery the last configurations used (found the folder of the file by the OS).
        self.restore_properties()

        # Files in the history.
        #if not self.m_comboBox_files.IsListEmpty(): # If have some history, set to the last used file.
        #    self.m_comboBox_files.IsListEmpty(0)

    #----------------------------------------------------------------------
    def restore_properties(self):
        ''' @brief Restore the current proprieties of the graphical elements.'''
        try:
            configHandle = wx.Config(CONFIG_FILE)

            def str_to_wxpoint(s):
                '''Convert a string tuple into a  wxPoint.'''
                p = re.findall('\d+', s)
                return wx.Point(int(p[0]), int(p[1]))
            def str_to_wxsize(s):
                '''Convert a string tuple into a  wxRect.'''
                p = re.findall('\d+', s)
                return wx.Size(int(p[0]), int(p[1]))

            entryCount = 0
            while True:
                entry = configHandle.GetNextEntry(entryCount)
                if not entry[0]:
                    break
                entryCount+=1 #Count the entry numbers and go to next one in next iteration.
                entry = entry[1]
                entry_value = configHandle.Read(entry)

                # Resize and reposition the window frame.
                if entry==GUI_POSITION_ENTRY:
                    self.SetPosition(str_to_wxpoint(entry_value))
                    continue
                elif entry==GUI_SIZE_ENTRY:
                    self.SetSize(str_to_wxsize(entry_value))
                    continue
                elif entry==GUI_NEWS_MESSAGE_ENTRY:
                    if entry_value=='True':
                        def wait_show_news_message():
                            if self.show_news_message():
                                configHandle = wx.Config(CONFIG_FILE)
                                configHandle.Write(GUI_NEWS_MESSAGE_ENTRY, 'False') # Doesn't show the message on next GUI startup.
                        wx.CallAfter(wait_show_news_message)
                    continue

                try:
                    wxElement_handle = self.__dict__[entry]
                    if not wxElement_handle.IsEnabled():
                        continue # Not enabled controls have not to have the values restored.
                    # Find the wxPython element handle to access the methods.
                    # Each wxPython object have a specific parameter value
                    # to be saved and restored in the software initialization.
                    if isinstance(wxElement_handle, wx._core.TextCtrl):
                        wxElement_handle.SetValue(entry_value)
                    elif isinstance(wxElement_handle, wx._core.CheckBox):
                        wxElement_handle.SetValue((True if entry_value=='True' else False))
                    elif isinstance(wxElement_handle, wx._core.CheckListBox):
                        value = re.split(',', entry_value)
                        for idx in range(wxElement_handle.GetCount()): # Reset all checked.
                            wxElement_handle.Check(idx, False)
                        for dist_checked in value: # Check only the founded names.
                            idx = wxElement_handle.FindString(dist_checked)
                            if idx!=wx.NOT_FOUND:
                                wxElement_handle.Check(idx, True)
                    elif isinstance(wxElement_handle, wx._core.SpinCtrl):
                        wxElement_handle.SetValue(int(entry_value))
                    elif isinstance(wxElement_handle, wx._core.SpinCtrlDouble):
                        wxElement_handle.SetValue(float(entry_value))
                    elif isinstance(wxElement_handle, wx._core.ComboBox):
                        if entry=='m_comboBox_files':
                            value = re.split(',', entry_value)
                            for element in value:
                                if element:
                                    wxElement_handle.Append(element)
                        else:
                            wxElement_handle.SetValue(entry_value)
                    elif isinstance(wxElement_handle, wx._core.ListBox):
                        wxElement_handle.SetSelection(wxElement_handle.FindString(entry_value))
                    elif isinstance(wxElement_handle, wx._core.Notebook):
                        wxElement_handle.SetSelection(int(entry_value))
                    # Others wxWidgets graphical elements with not saved configurations.
                    #elif isinstance(wxElement_handle, wx._core.):
                    #elif isinstance(wxElement_handle, wx._core.):configHandle
                    #elif isinstance(wxElement_handle, wx._core.StaticBitmap):
                    #elif isinstance(wxElement_handle, wx._core.Panel):
                    #elif isinstance(wxElement_handle, wx._core.Button):
                    #elif isinstance(wxElement_handle, wx._core.StaticText):
                except KeyError:
                    continue

            del configHandle # Close the file / Windows registry sock.
        except Exception as e:
            logger.log(DEBUG_OVERVIEW, 'Configurations not recovered: <'+str(e)+'>.')

    #----------------------------------------------------------------------
    def save_properties(self):
        ''' @brief Save the current proprieties of the graphical elements.'''
        try:
            configHandle = wx.Config(CONFIG_FILE)

            # Save position and size.
            configHandle.Write(GUI_POSITION_ENTRY, str(self.GetPosition()))
            configHandle.Write(GUI_SIZE_ENTRY, str(self.GetSize()))

            # Sweep all elements in `self()` to find the graphical ones
            # instance of the wxPython and salve the specific configuration.
            for wxElement_name, wxElement_handle in self.__dict__.items():
                try:
                    # Each wxPython object have a specific parameter value
                    # to be saved and restored in the software initialization.
                    if isinstance(wxElement_handle, wx._core.TextCtrl) and not wxElement_name in ['m_textCtrl_messages', 'm_text_credits', 'm_text_saveas']:
                        # Save each TextCtrl (TextBox) that is not the status messages or credits.
                        configHandle.Write(wxElement_name, wxElement_handle.GetValue())
                    elif isinstance(wxElement_handle, wx._core.CheckBox):
                        configHandle.Write(wxElement_name, ('True' if wxElement_handle.GetValue() else 'False'))
                    elif isinstance(wxElement_handle, wx._core.CheckListBox):
                        value = [wxElement_handle.GetString(idx) for idx in wxElement_handle.GetCheckedItems()]
                        configHandle.Write(wxElement_name, ','.join(value))
                    elif isinstance(wxElement_handle, wx._core.SpinCtrl) or isinstance(wxElement_handle, wx._core.SpinCtrlDouble):
                        configHandle.Write(wxElement_name, str(wxElement_handle.GetValue()))
                    elif isinstance(wxElement_handle, wx._core.ComboBox):
                        if wxElement_name=='m_comboBox_files': # Save the file history.
                            value = [wxElement_handle.GetString(idx) for idx in range(wxElement_handle.GetCount())]
                            configHandle.Write(wxElement_name, ','.join(value))
                        else:
                            configHandle.Write(wxElement_name, wxElement_handle.GetValue())
                    elif isinstance(wxElement_handle, wx._core.ListBox):
                        configHandle.Write(wxElement_name, wxElement_handle.GetStringSelection())
                    elif isinstance(wxElement_handle, wx._core.Notebook):
                        configHandle.Write(wxElement_name, str(wxElement_handle.GetSelection()))
                    # Others wxWidgets graphical elements with not saved configurations.
                    #elif isinstance(wxElement_handle, wx._core.):configHandle
                    #elif isinstance(wxElement_handle, wx._core.StaticBitmap):
                    #elif isinstance(wxElement_handle, wx._core.Panel):
                    #elif isinstance(wxElement_handle, wx._core.Button):
                    #elif isinstance(wxElement_handle, wx._core.StaticText):
                except KeyError:
                    continue

            del configHandle # Close the file / Windows registry sock.
        except Exception as e:
            logger.log(DEBUG_OVERVIEW, 'Configurations not saved: <'+str(e)+'>.')

    def show_news_message(self):
        '''Shows a message bos if the news of the last version installed.'''
        history_file = open(os.path.join(kicostPath, 'HISTORY.rst') )
        history = history_file.read()
        history_file.close()
        search_news = re.compile('History\s+[\=\-\_]+\s+(?P<version>[\w\.]+)\s*\((?P<data>.+)\)\s+[\=\-\_]+\s+(?P<news>(?:\n|.)*?)\s+[\d\.]+', re.IGNORECASE)
        news = re.search(search_news, history)
        dlg = wx.MessageDialog(self,
                               news.group('news'),
                               'NEWS of KiCost v.{v} release from {d}'.format(v=news.group('version'), d=news.group('data')),
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
        return True



#######################################################################

def kicost_gui(files=None):
    ''' @brief Load the graphical interface.
        @param String file file names or list.
        (it will be used for plugin implementation on future KiCad6-Eeschema).
    '''
    app = wx.App(redirect=False)
    frame = formKiCost(None)

    class GUI_LoggerHandler(object):
        def __init__(self, aWxTextCtrl):
            #super(self.__class__, self).__init__()
            self.area = aWxTextCtrl
        def write(self, msg):
            #self.area.AppendText(msg)
            # Necessary the call bellow and not above
            # because of the KiCost threads.
            wx.CallAfter(self.area.AppendText, msg)
            #wx.CallAfter(frame.m_textCtrl_messages.AppendText, msg)
        def flush(self):
            sys.__stdout__.flush()

    class GUI_ETAHandler(object):
        def __init__(self):
            pass
        def write(self, msg):
            try:
                # Try to read a process bar model, with error, is really a error message.
                # Model:
                #Progress: 100%|███████████████████████████████| 24/24 [00:26<00:00,  1.56s/part]
                # Second https://github.com/tqdm/tqdm/issues/172 is necessary this work around,
                # until they finish the v5.
                wx.CallAfter(frame.m_gauge_process.SetValue,
                    int(re.findall('^.*\s(\d+)\%', msg)[0])) # Perceptual.
                wx.CallAfter(frame.m_staticText_progressInfo.SetLabel,
                    re.findall('\|+?\s(.*)$', msg)[0]) # Eta.
            except:
                sys.__stderr__.write(msg)
        def flush(self):
            sys.__stderr__.flush()

    # Redirect the logger to the GUI area.
    sys.stdout = GUI_LoggerHandler(frame.m_textCtrl_messages)
    sys.stderr = GUI_ETAHandler()

    if files:
        frame.m_comboBox_files.SetValue(SEP_FILES.join(files))
        frame.updateOutputFilename()

    frame.Show()
    app.MainLoop()

    # Restore the channel print output to terminal.
    # Necessary if KiCost was called by other software?
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__


def kicost_gui_runterminal(args):
    ''' @brief Execute the `fileName` under KiCost loading the
        graphical interface.

        The difference of the normal execution is that the log and
        process bar is not redirected to the GUI, staying on terminal.

        @param List of the file name.
    '''
    app = wx.App(redirect=False)
    frame = formKiCost(None)

    files = args.input
    frame.m_comboBox_files.SetValue(SEP_FILES.join(files))
    frame.updateOutputFilename()

    options_cmd=''
    for k_a in list(args.__dict__.keys()):
        if k_a=='input' or k_a=='user' or k_a=='guide' or k_a=='help':
            pass
        elif isinstance(args.__dict__[k_a], bool) and args.__dict__[k_a]==True:
            options_cmd += '--' + k_a
        elif isinstance(args.__dict__[k_a], float) or isinstance(args.__dict__[k_a], int) \
            and args.__dict__[k_a]:
                options_cmd += '--' + k_a + str(args.__dict__[k_a])
        elif isinstance(args.__dict__[k_a], list) and args.__dict__[k_a]:
            options_cmd += '--' + k_a + ' '.join(args.__dict__[k_a])
        #else args.__dict__[k_a]:
        #    options_cmd += '--' + k_a + ' '.join(args.__dict__[k_a])

    frame.m_textCtrlextracmd.SetValue(options_cmd)

    frame.updateEDAselection()
    frame.run()
