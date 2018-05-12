# -*- coding: utf-8 -*- 
# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo Guillardi Junior
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

# Libraries.
try:
    import wx # wxWidgets for Python.
except ImportError:
    raise ImportError('wxPython package not recognised.')
import webbrowser # To update informations.
import sys, os, subprocess # To access OS commands and run in the shell.
import threading
import time # To elapse time.
import platform # To check the system platform when open the XLS file.
import tempfile # To create the temporary log file.
from datetime import datetime # To create the log name, when asked to save.
from distutils.version import StrictVersion # To comparasion of versions.
import re # Regular expression parser.

from . import __version__ # Version control by @xesscorp.
from .kicost import *  # kicost core functions.
from .distributors import distributor_dict, fake_browser # Use the configurations alredy made to get KiCost last version.
from .eda_tools import eda_tool_dict
from .eda_tools.eda_tools import file_eda_match

__all__ = ['kicost_gui', 'kicost_gui_run']

# Guide definitions.
FILE_HIST_QTY = 10
SEP_FILES = '\n' # File separator in the comboBox.
WILDCARD = "BoM compatible formats (*.xml,*.csv)|*.xml;*.csv|"\
            "KiCad/Altium BoM file (*.xml)|*.xml|" \
            "Proteus/Generic BoM file (*.csv)|*.csv"
CONFIG_FILE = 'KiCost' # Config file for Linux and Windows registry key for KiCost configurations.
GUI_SIZE_ENTRY = 'GUI_size'
GUI_POSITION_ENTRY = 'GUI_position'
PAGE_OFFICIAL = 'https://xesscorp.github.io/KiCost/'
PAGE_UPDATE = 'https://pypi.python.org/pypi/kicost' # Page with the last official version.
#https://github.com/xesscorp/KiCost/blob/master/kicost/version.py



#======================================================================
def open_file(filepath):
    '''@brief Open a file with the default application by yht different OS.
       @param filepath str() file name.
    '''
    if sys.platform.startswith('darwin'): # Mac-OS.
        subprocess.call(('open', filepath))
    elif sys.platform.startswith('windows'): # Windows.
        os.startfile(filepath)
    elif sys.platform.startswith('linux'): # Linux.
        subprocess.call(('xdg-open', filepath))
    else:
        print('Not recognized OS.')


#======================================================================
class FileDropTarget( wx.FileDropTarget ):
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
class menuDistributors( wx.Menu ):
    ''' @brief Menu of the istributor checkbox list. Provide select all, unselect and toggle hotkey.
        @param TextBox handle.
    '''
    def __init__( self, parent ):
        ''' @brief Constructor.'''
        super(menuDistributors, self).__init__()
        self.parent = parent
        
        mmi = wx.MenuItem(self, wx.NewId(), 'Select &all')
        self.Append(mmi)
        self.Bind(wx.EVT_MENU, self.selectAll, mmi)
        
        mmi = wx.MenuItem(self, wx.NewId(), '&Unselect all')
        self.Append(mmi)
        self.Bind(wx.EVT_MENU, self.unselectAll, mmi)
        
        mmi = wx.MenuItem(self, wx.NewId(), '&Toggle')
        self.Append(mmi)
        self.Bind(wx.EVT_MENU, self.toggleAll, mmi)
    
    def selectAll( self, event ):
        ''' @brief Select all distributor that exist.'''
        event.Skip()
        for idx in range(self.parent.m_checkList_dist.GetCount()):
            if not self.parent.m_checkList_dist.IsChecked(idx):
                self.parent.m_checkList_dist.Check(idx)
    
    def unselectAll( self, event ):
        ''' @brief Unselect all distributor that exist.'''
        event.Skip()
        for idx in range(self.parent.m_checkList_dist.GetCount()):
            if self.parent.m_checkList_dist.IsChecked(idx):
                self.parent.m_checkList_dist.Check(idx, False)
    
    def toggleAll( self, event ):
        ''' @brief Toggle all distributor that exist.'''
        event.Skip()
        for idx in range(self.parent.m_checkList_dist.GetCount()):
            if self.parent.m_checkList_dist.IsChecked(idx):
                self.parent.m_checkList_dist.Check(idx, False)
            else:
                self.parent.m_checkList_dist.Check(idx)


#======================================================================
class menuMessages( wx.Menu ):
    ''' @brief Menu of the messages text. Provide copy and save options.
        @param TextBox handle.
    '''
    def __init__( self, parent ):
        ''' @brief Constructor.'''
        super(menuMessages, self).__init__()
        self.parent = parent
        
        mmi = wx.MenuItem(self, wx.NewId(), '&Purge')
        self.Append(mmi)
        self.Bind(wx.EVT_MENU, self.purgeMessages, mmi)
        
        self.AppendSeparator()
        
        mmi = wx.MenuItem(self, wx.NewId(), '&Copy to clipboard')
        self.Append(mmi)
        self.Bind(wx.EVT_MENU, self.copyMessages, mmi)
        
        mmi = wx.MenuItem(self, wx.NewId(), 'Cut to clipboard')
        self.Append(mmi)
        self.Bind(wx.EVT_MENU, self.cutMessages, mmi)
        
        mmi = wx.MenuItem(self, wx.NewId(), '&Save')
        self.Append(mmi)
        self.Bind(wx.EVT_MENU, self.saveMessages, mmi)
        
        mmi = wx.MenuItem(self, wx.NewId(), 'S&ave and clear')
        self.Append(mmi)
        self.Bind(wx.EVT_MENU, self.saveClearMessages, mmi)
        
        mmi = wx.MenuItem(self, wx.NewId(), '&Open externally')
        self.Append(mmi)
        self.Bind(wx.EVT_MENU, self.openMessages, mmi)
        
    
    def copyMessages( self, event ):
        ''' @brief Copy the warning/error/log messages to clipboard.'''
        event.Skip()
        clipdata = wx.TextDataObject()
        clipdata.SetText( self.parent.m_textCtrl_messages.GetValue() )
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()
    
    def cutMessages( self, event ):
        ''' @brief Cut the warning/error/log messages to clipboard.'''
        event.Skip()
        self.purgeMessages(event)
        self.copyMessages(event)
    
    def purgeMessages( self, event ):
        ''' @brief Clear message box.'''
        event.Skip()
        self.parent.m_textCtrl_messages.Clear()
    
    def saveMessages( self, event ):
        ''' @brief Save the messages as a text "KiCost*.log" file.'''
        event.Skip()
        actualDir = (os.getcwd() if self.parent.m_comboBox_files.GetValue() else \
            os.path.dirname(os.path.abspath( self.parent.m_comboBox_files.GetValue() )) )
        dlg = wx.FileDialog(
            self.parent, message = "Save log as...",
            defaultDir = actualDir, 
            defaultFile = "KiCost " + datetime.now().strftime('%Y-%m-%d %Hh%Mmin%Ss'),
            wildcard = "Log file (*.log)|*.log",
            style = wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT
            )
        dlg.SetFilterIndex(0)
        if dlg.ShowModal() == wx.ID_OK:
            f = open( dlg.GetPath() , 'w')
            f.write( self.parent.m_textCtrl_messages.GetValue() )
            f.close()
            wx.MessageBox('The log file as saved.', 'Info', wx.OK | wx.ICON_INFORMATION)
        dlg.Destroy()
    
    def saveClearMessages( self, event ):
        '''@brief Save the messages and clear the log in the guide.'''
        event.Skip()
        self.saveMessages(event)
        self.purgeMessages(event)
    
    def openMessages( self, event ):
        ''' @brief Save the messages in a temporary file and open it in the default text editor before sytem deletation.'''
        event.Skip()
        #TODO - not working on Ubuntu
        #self.parent.m_textCtrl_messages.AppendText('\naqui\nhjhk')
        with tempfile.NamedTemporaryFile(prefix='KiCost_', suffix='.log', delete=True, mode='w') as temp:
            temp.write( self.parent.m_textCtrl_messages.GetValue() )
            open_file(temp.name)
            temp.close()


#======================================================================
class formKiCost ( wx.Frame ):
    ''' @brief Main frame / form of KiCost GUI.'''
    
    def __init__( self, parent ):
        ''' @brief Constructor, code generated by wxFormBuilder tool.'''
        #### **  Begin of the guide code generated by wxFormBulilder software, available in <https://github.com/wxFormBuilder/wxFormBuilder/>  ** ####
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"KiCost", pos = wx.DefaultPosition, size = wx.Size( 446,351 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
        
        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )
        
        bSizer1 = wx.BoxSizer( wx.VERTICAL )
        
        self.m_notebook1 = wx.Notebook( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_panel1 = wx.Panel( self.m_notebook1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        self.m_panel1.SetToolTip( u"Basic controls, BoM selection and supported distributors." )
        
        bSizer3 = wx.BoxSizer( wx.VERTICAL )
        
        sbSizer2 = wx.StaticBoxSizer( wx.StaticBox( self.m_panel1, wx.ID_ANY, u"Files" ), wx.HORIZONTAL )
        
        m_comboBox_filesChoices = []
        self.m_comboBox_files = wx.ComboBox( sbSizer2.GetStaticBox(), wx.ID_ANY, u"Not selected files", wx.DefaultPosition, wx.DefaultSize, m_comboBox_filesChoices, 0 )
        self.m_comboBox_files.SetToolTip( u"BoM(s) file(s) to scrape.\nClick on the arrow to see/select one of the history files." )
        
        sbSizer2.Add( self.m_comboBox_files, 1, wx.ALL, 5 )
        
        self.m_button_openfile = wx.Button( sbSizer2.GetStaticBox(), wx.ID_ANY, u"Choose BoM", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_button_openfile.SetToolTip( u"Click to choose the BoM(s) file(s)." )
        
        sbSizer2.Add( self.m_button_openfile, 0, wx.ALL, 5 )
        
        
        bSizer3.Add( sbSizer2, 0, wx.EXPAND|wx.TOP, 5 )
        
        bSizer4 = wx.BoxSizer( wx.HORIZONTAL )
        
        sbSizer3 = wx.StaticBoxSizer( wx.StaticBox( self.m_panel1, wx.ID_ANY, u"Distributors to scrape" ), wx.VERTICAL )
        
        m_checkList_distChoices = [wx.EmptyString]
        self.m_checkList_dist = wx.CheckListBox( sbSizer3.GetStaticBox(), wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, m_checkList_distChoices, 0 )
        self.m_checkList_dist.SetToolTip( u"Select the web distributor (or local) that will be used to scrape the prices.\nClick rigth to hot option." )
        
        sbSizer3.Add( self.m_checkList_dist, 1, wx.ALL|wx.EXPAND, 5 )
        
        
        bSizer4.Add( sbSizer3, 1, wx.EXPAND|wx.TOP|wx.LEFT, 5 )
        
        wSizer1 = wx.WrapSizer( wx.VERTICAL )
        
        bSizer6 = wx.BoxSizer( wx.VERTICAL )
        
        sbSizer31 = wx.StaticBoxSizer( wx.StaticBox( self.m_panel1, wx.ID_ANY, u"EDAs" ), wx.VERTICAL )
        
        m_listBox_edatoolChoices = []
        self.m_listBox_edatool = wx.ListBox( sbSizer31.GetStaticBox(), wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, m_listBox_edatoolChoices, 0 )
        self.m_listBox_edatool.SetToolTip( u"Choose the correct EDA software corresponding to the BoM file." )
        
        sbSizer31.Add( self.m_listBox_edatool, 1, wx.ALL|wx.EXPAND, 5 )
        
        self.m_checkBox_openXLS = wx.CheckBox( sbSizer31.GetStaticBox(), wx.ID_ANY, u"Open spreadsheet", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_checkBox_openXLS.SetValue(True) 
        self.m_checkBox_openXLS.SetToolTip( u"Open the spreadsheet after finish the KiCost scrape." )
        
        sbSizer31.Add( self.m_checkBox_openXLS, 0, wx.ALL, 5 )
        
        
        bSizer6.Add( sbSizer31, 1, wx.TOP|wx.RIGHT|wx.EXPAND, 5 )
        
        self.m_button_run = wx.Button( self.m_panel1, wx.ID_ANY, u"KiCost it!", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_button_run.SetToolTip( u"Click to run KiCost." )
        
        bSizer6.Add( self.m_button_run, 0, wx.ALL, 5 )
        
        
        wSizer1.Add( bSizer6, 1, wx.RIGHT|wx.EXPAND, 5 )
        
        
        bSizer4.Add( wSizer1, 1, wx.EXPAND, 5 )
        
        
        bSizer3.Add( bSizer4, 1, wx.EXPAND, 5 )
        
        fgSizer1 = wx.FlexGridSizer( 0, 4, 0, 0 )
        fgSizer1.SetFlexibleDirection( wx.BOTH )
        fgSizer1.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
        
        self.m_gauge_process = wx.Gauge( self.m_panel1, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL )
        self.m_gauge_process.SetValue( 0 ) 
        self.m_gauge_process.SetToolTip( u"Percentage of the scrape process elapsed." )
        
        fgSizer1.Add( self.m_gauge_process, 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL, 5 )
        
        self.m_staticText_progressInfo = wx.StaticText( self.m_panel1, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText_progressInfo.Wrap( -1 )
        self.m_staticText_progressInfo.SetToolTip( u"Progress infromation." )
        
        fgSizer1.Add( self.m_staticText_progressInfo, 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, 5 )
        
        
        bSizer3.Add( fgSizer1, 0, wx.EXPAND, 5 )
        
        self.m_staticText9 = wx.StaticText( self.m_panel1, wx.ID_ANY, u"Warnings, debug and error messages:", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText9.Wrap( -1 )
        bSizer3.Add( self.m_staticText9, 0, wx.ALL|wx.EXPAND, 5 )
        
        self.m_textCtrl_messages = wx.TextCtrl( self.m_panel1, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( -1,4 ), wx.HSCROLL|wx.TE_MULTILINE|wx.TE_READONLY )
        self.m_textCtrl_messages.SetToolTip( u"Process messages and warnings.\nClick right to copy or save the log." )
        self.m_textCtrl_messages.SetMinSize( wx.Size( -1,4 ) )
        
        bSizer3.Add( self.m_textCtrl_messages, 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 5 )
        
        
        self.m_panel1.SetSizer( bSizer3 )
        self.m_panel1.Layout()
        bSizer3.Fit( self.m_panel1 )
        self.m_notebook1.AddPage( self.m_panel1, u"BoM", True )
        self.m_panel2 = wx.Panel( self.m_notebook1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        self.m_panel2.SetToolTip( u"KiCost general configurations tab." )
        
        bSizer8 = wx.BoxSizer( wx.VERTICAL )
        
        wSizer2 = wx.WrapSizer( wx.HORIZONTAL )
        
        bSizer9 = wx.BoxSizer( wx.VERTICAL )
        
        self.m_staticText2 = wx.StaticText( self.m_panel2, wx.ID_ANY, u"Parallel process", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText2.Wrap( -1 )
        bSizer9.Add( self.m_staticText2, 0, wx.ALL, 5 )
        
        self.m_spinCtrl_np = wx.SpinCtrl( self.m_panel2, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 1, 30, 6 )
        self.m_spinCtrl_np.SetToolTip( u"Set the number of parallel processes used for web scraping the parts data." )
        
        bSizer9.Add( self.m_spinCtrl_np, 0, wx.ALL, 5 )
        
        self.m_staticText3 = wx.StaticText( self.m_panel2, wx.ID_ANY, u"Scrap retries", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText3.Wrap( -1 )
        bSizer9.Add( self.m_staticText3, 0, wx.ALL, 5 )
        
        self.m_spinCtrl_retries = wx.SpinCtrl( self.m_panel2, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 4, 200, 0 )
        self.m_spinCtrl_retries.SetToolTip( u"Specify the number of attempts to retrieve part data from a website." )
        
        bSizer9.Add( self.m_spinCtrl_retries, 0, wx.ALL, 5 )
        
        self.m_staticText7 = wx.StaticText( self.m_panel2, wx.ID_ANY, u"Throttling delay (s)", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText7.Wrap( -1 )
        bSizer9.Add( self.m_staticText7, 0, wx.ALL, 5 )
        
        self.m_spinCtrlDouble_throttling = wx.SpinCtrlDouble( self.m_panel2, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 0, 5, 0, 0.1 )
        self.m_spinCtrlDouble_throttling.SetToolTip( u"Specify minimum delay (in seconds) between successive accesses to a distributor's website.\nUsed when the websites not accept successive accesses." )
        
        bSizer9.Add( self.m_spinCtrlDouble_throttling, 0, wx.ALL, 5 )
        
        
        wSizer2.Add( bSizer9, 1, wx.TOP|wx.LEFT, 5 )
        
        bSizer11 = wx.BoxSizer( wx.VERTICAL )
        
        self.m_checkBox_collapseRefs = wx.CheckBox( self.m_panel2, wx.ID_ANY, u"Collapse refs", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_checkBox_collapseRefs.SetValue(True) 
        self.m_checkBox_collapseRefs.SetToolTip( u"Collapse the references in the spreadsheet.\n'R1,R2,R3,R4,R9' become 'R1-R4,R9' with checked." )
        
        bSizer11.Add( self.m_checkBox_collapseRefs, 0, wx.ALL, 5 )
        
        self.m_staticText8 = wx.StaticText( self.m_panel2, wx.ID_ANY, u"Debug level", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText8.Wrap( -1 )
        bSizer11.Add( self.m_staticText8, 0, wx.ALL, 5 )
        
        self.m_spinCtrl_debugLvl = wx.SpinCtrl( self.m_panel2, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.SP_ARROW_KEYS, 0, 10, 0 )
        bSizer11.Add( self.m_spinCtrl_debugLvl, 0, wx.ALL, 5 )
        
        self.m_checkBox_quite = wx.CheckBox( self.m_panel2, wx.ID_ANY, u"Quiet mode", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_checkBox_quite.SetToolTip( u"Enable quiet mode with no warnings." )
        
        bSizer11.Add( self.m_checkBox_quite, 0, wx.ALL, 5 )
        
        self.m_checkBox_overwrite = wx.CheckBox( self.m_panel2, wx.ID_ANY, u"Overwrite file", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_checkBox_overwrite.SetValue(True) 
        self.m_checkBox_overwrite.SetToolTip( u"Allow overwriting of an existing spreadsheet." )
        
        bSizer11.Add( self.m_checkBox_overwrite, 0, wx.ALL, 5 )
        
        
        wSizer2.Add( bSizer11, 1, wx.TOP|wx.RIGHT, 5 )
        
        
        bSizer8.Add( wSizer2, 1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTER_HORIZONTAL, 5 )
        
        self.m_staticText4 = wx.StaticText( self.m_panel2, wx.ID_ANY, u"Extra commands", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText4.Wrap( -1 )
        bSizer8.Add( self.m_staticText4, 0, wx.ALL, 5 )
        
        self.m_textCtrlextracmd = wx.TextCtrl( self.m_panel2, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_textCtrlextracmd.SetToolTip( u" Here use the kicost extra commands. In the terminal/command type`kicost --help` to check the list." )
        
        bSizer8.Add( self.m_textCtrlextracmd, 0, wx.ALL|wx.EXPAND, 5 )
        
        
        self.m_panel2.SetSizer( bSizer8 )
        self.m_panel2.Layout()
        bSizer8.Fit( self.m_panel2 )
        self.m_notebook1.AddPage( self.m_panel2, u"KiCost config", False )
        self.m_panel3 = wx.Panel( self.m_notebook1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        self.m_panel3.SetToolTip( u"About the software, version installation and update found." )
        
        bSizer2 = wx.BoxSizer( wx.VERTICAL )
        
        bSizer10 = wx.BoxSizer( wx.HORIZONTAL )
        
        self.m_bitmap_icon = wx.StaticBitmap( self.m_panel3, wx.ID_ANY, wx.NullBitmap, wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizer10.Add( self.m_bitmap_icon, 0, wx.ALL, 5 )
        
        bSizer111 = wx.BoxSizer( wx.VERTICAL )
        
        self.m_staticText_version = wx.StaticText( self.m_panel3, wx.ID_ANY, u"MyLabel", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText_version.Wrap( -1 )
        bSizer111.Add( self.m_staticText_version, 1, wx.ALL, 5 )
        
        self.m_staticText_update = wx.StaticText( self.m_panel3, wx.ID_ANY, u"Update info", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText_update.Wrap( -1 )
        bSizer111.Add( self.m_staticText_update, 0, wx.ALL, 5 )
        
        
        bSizer10.Add( bSizer111, 1, wx.EXPAND, 5 )
        
        
        bSizer2.Add( bSizer10, 0, wx.ALL|wx.EXPAND, 5 )
        
        self.m_staticText_credits = wx.StaticText( self.m_panel3, wx.ID_ANY, u"MyLabel", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText_credits.Wrap( -1 )
        bSizer2.Add( self.m_staticText_credits, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL|wx.EXPAND, 5 )
        
        
        self.m_panel3.SetSizer( bSizer2 )
        self.m_panel3.Layout()
        bSizer2.Fit( self.m_panel3 )
        self.m_notebook1.AddPage( self.m_panel3, u"About", False )
        
        bSizer1.Add( self.m_notebook1, 1, wx.EXPAND |wx.ALL, 5 )
        
        
        self.SetSizer( bSizer1 )
        self.Layout()
        
        self.Centre( wx.BOTH )
        
        # Connect Events
        self.Bind( wx.EVT_CLOSE, self.app_close )
        self.m_notebook1.Bind( wx.EVT_NOTEBOOK_PAGE_CHANGED, self.wxPanel_change )
        self.m_comboBox_files.Bind( wx.EVT_COMBOBOX, self.m_comboBox_files_selecthist )
        self.m_button_openfile.Bind( wx.EVT_BUTTON, self.button_openfile )
        self.m_checkList_dist.Bind( wx.EVT_RIGHT_DOWN, self.m_textCtrl_distributors_rClick )
        self.m_button_run.Bind( wx.EVT_BUTTON, self.button_run )
        self.m_textCtrl_messages.Bind( wx.EVT_RIGHT_DOWN, self.m_textCtrl_messages_rClick )
        self.m_bitmap_icon.Bind( wx.EVT_LEFT_DOWN, self.m_bitmap_icon_click )
        
        #### **  End of the guide code generated by wxFormBulilder software, available in <https://github.com/wxFormBuilder/wxFormBuilder/>  ** ####
        
        self.updateChecked = False 
        self.set_properties()
        self.SetDropTarget( FileDropTarget(self) ) # Start the drop file in all the window.
        self.m_textCtrl_messages.AppendText( 'Loaded KiCost v.' + __version__ )
    
    def __del__( self ):
        pass

    # Virtual event handlers, overide them in your derived class

    #----------------------------------------------------------------------
    def app_close( self, event ):
        ''' @brief Close event, used to call the save settings.'''
        event.Skip()
        self.save_properties()

    #----------------------------------------------------------------------
    def m_bitmap_icon_click( self, event ):
        ''' @brief Open the official software web page in the default browser.'''
        event.Skip()
        webbrowser.open(PAGE_OFFICIAL)

    #----------------------------------------------------------------------
    def wxPanel_change( self, event ):
        ''' @brief Check version to update if the "About" tab.'''
        event.Skip()
        if event.GetSelection()==2: # Is the last page (about page).
            
            def checkUpdate():
                '''Check for updates.'''
                try:
                    updateChecked = self.updateChecked
                except:
                    updateChecked = False
                if not updateChecked:
                    self.m_staticText_update.SetLabel('Checking by updates...')
                    try:
                        html = fake_browser(PAGE_UPDATE)
                        offical_last_version = re.findall('kicost (\d+\.\d+\.\d+)', str(html), flags=re.IGNORECASE)[0]
                        if StrictVersion(offical_last_version) > StrictVersion(__version__):
                            self.m_staticText_update.SetLabel('New version (v.'
                                + offical_last_version
                                + ') founded.\nClick <here> to update.')
                            self.m_staticText_update.Bind( wx.EVT_LEFT_UP, self.m_staticText_update_click )
                        else:
                            self.m_staticText_update.SetLabel('KiCost is up to date.')
                    except:
                        self.m_staticText_update.SetLabel('Update information not founded.')
                    finally:
                        self.updateChecked = True
            
            wx.CallLater(50, checkUpdate) # Thread optimized for graphical elements change.

    #----------------------------------------------------------------------
    def m_textCtrl_messages_rClick( self, event ):
        ''' @brief Open the context menu with save log options.'''
        event.Skip()
        self.PopupMenu(menuMessages(self), event.GetPosition())

    #----------------------------------------------------------------------
    def m_textCtrl_distributors_rClick( self, event ):
        ''' @brief Open the context menu with distributors options.'''
        event.Skip()
        self.PopupMenu(menuDistributors(self), event.GetPosition())

    #----------------------------------------------------------------------
    def m_comboBox_files_selecthist( self, event):
        ''' @brief Update the select EDA module tool when changed the file selected in the history, update the order and delete if file not existent.'''
        event.Skip()
        # Check if the file in the file name exist and
        # update the history sequence, if don't, remove it.
        histSelected = event.GetSelection()
        fileNames = event.GetString()
        self.m_comboBox_files.Delete(histSelected)
        if all(os.path.isfile(f) for f in re.split(SEP_FILES, fileNames) ):
            self.m_comboBox_files.Insert( fileNames, 0 )
            self.updateEDAselection() # Auto-select the EDA module.
        else:
            self.m_comboBox_files.SetValue('')

    #----------------------------------------------------------------------
    def updateEDAselection( self ):
        ''' @brief Update the EDA selection in the listBox based on the comboBox actual text.'''
        fileNames = re.split(SEP_FILES, self.m_comboBox_files.GetValue())
        if len(fileNames)==1:
            eda_module = file_eda_match(fileNames[0])
            if eda_module:
                self.m_listBox_edatool.SetSelection( self.m_listBox_edatool.FindString(eda_tool_dict[eda_module]['label']) )
        elif len(fileNames)>1:
            # Check if all the EDA are the same. For different ones,
            # the guide is not able now to deal, need improvement
            # on `self.m_listBox_edatool`.
            eda_module = file_eda_match(fileNames[0])
            for fName in fileNames[1:]:
                if file_eda_match(fName) != eda_module:
                    return
            if eda_module:
                self.m_listBox_edatool.SetSelection( self.m_listBox_edatool.FindString(eda_tool_dict[eda_module]['label']) )

    #----------------------------------------------------------------------
    def m_staticText_update_click( self, event ):
        ''' @brief Open the page to download the last version.'''
        event.Skip()
        #print('Download the update and install -- missing, running manually')
        webbrowser.open(PAGE_UPDATE)

    #----------------------------------------------------------------------
    def button_openfile( self, event ):
        """ @brief Create and show the Open FileDialog """
        event.Skip()
        
        actualDir = (os.getcwd() if self.m_comboBox_files.GetValue() else \
            os.path.dirname(os.path.abspath( self.m_comboBox_files.GetValue() )) )
        
        dlg = wx.FileDialog(
            self, message = "Select BoM(s)",
            defaultDir = actualDir, 
            defaultFile = "",
            wildcard = WILDCARD,
            style = wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR
            )
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
            self.addFile( paths )
        dlg.Destroy()

    #----------------------------------------------------------------------
    def addFile( self, filesName ):
        ''' @brief Add the file(s) to the history, updating it (and delete the too old).'''
        fileBOM = SEP_FILES.join( sorted(filesName, key=str.lower) ) # Add the files sorted.
        if self.m_comboBox_files.FindString(fileBOM)==wx.NOT_FOUND:
            self.m_comboBox_files.Insert( fileBOM, 0 )
        self.m_comboBox_files.SetValue( fileBOM )
        try:
            self.m_comboBox_files.Delete(FILE_HIST_QTY-1) # Keep 10 files on history.
        except:
            pass
        self.updateEDAselection()

    #----------------------------------------------------------------------
    def button_run( self, event ):
        ''' @brief Call to run KiCost.'''
        event.Skip()
        def run_kicost_guide():
            class EtaStream(object):
                def __init__(self, widget):
                    #super(self.__class__, self).__init__()
                    pass
                def write(self, bar):
                    sys.stderr.write(bar)
                    try:
                        #Progress:   3%|█                               | 3/90 [00:13<19:42, 13.59s/part]
                        print('-------', bar)
                        #perc = re.findall('(\d)\%\|')[0]
                        #desc = re.findall('\| (.+)$')[0]
                        #print('---', perc, desc)#TODO
                        #self.m_gauge_process.SetValue(perc)
                        #self.m_staticText_progressInfo.SetLabel(desc)
                    except:
                        pass
                    def flush(self):
                        sys.stderr.flush()
            class GUILoggingHandler(object):
                def __init__(self, widget):
                    #super(self.__class__, self).__init__()
                    self.widget = widget
                def write(self, msg):
                    try:
                        self.widget.AppendText( msg )
                    except:
                        sys.__stdout__(msg)
                def flush(self):#TODO
                    sys.stderr.flush()
            self.m_button_openfile.Enable( False )
            #sys.stdout = GUILoggingHandler(self.m_textCtrl_messages)
            #sys.errout = GUILoggingHandler(self.m_textCtrl_messages)
            
            self.save_properties() # Save the current graphical configuration before call the KiCost motor.
            self.run() # Run KiCost.
            
            # Restore the channel print output to terminal.
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            
            self.m_button_openfile.Enable( True )
        def run_kicost_guide2():
            '''Run the as a Thread out of the box wxPython'''
            self.m_gauge_process.SetValue(0)
            kicost_motor_thread = threading.Thread(target=run_kicost_guide)
            kicost_motor_thread.start()
        wx.CallLater(10, run_kicost_guide2) # Necessary to not '(core dumped)' with wxPython.

    #----------------------------------------------------------------------
    def run( self ):
        ''' @brief Run KiCost.
            Run KiCost in the GUI interface updating the process bar and messages.'''
        #self.m_gauge_process.SetValue(0)
        #self.m_textCtrl_messages.Clear() # Clear the messages to appear just the last run.
        
        class argments:
            pass
        args = argments()
        
        args.input = re.split(SEP_FILES, self.m_comboBox_files.GetValue())
        for f in args.input:
            if not os.path.isfile(f):
                print('No valid file(s) selected.')
                return # Not a valid file(s).
        
        spreadsheet_file = re.split(SEP_FILES, self.m_comboBox_files.GetValue())
        if len(spreadsheet_file)==1:
            spreadsheet_file = os.path.splitext( spreadsheet_file[0] )[0] + '.xlsx'
        else:
            spreadsheet_file = output_filename_multipleinputs( spreadsheet_file )
        # Handle case where output is going into an existing spreadsheet file.
        if os.path.isfile(spreadsheet_file):
            if not self.m_checkBox_overwrite.GetValue():
                dlg = wx.MessageDialog(self, 
                    "The file output \'{}\' already exit, do you wnat overwrite?".format(
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
        args.output = spreadsheet_file
        
        if self.m_textCtrlextracmd.GetValue():
            extra_commands = ' ' + self.m_textCtrlextracmd.GetValue()
        else:
            extra_commands = []
        
        def str_to_arg(commands):
            try:
                for c in commands:
                    try:
                        return ''.join( re.findall(c+' (.+)', extra_commands))
                    except:
                        continue
            except:
                pass
            finally:
                return ''
        args.fields = str_to_arg(['--fields', '-f']).split()
        args.ignore_fields = str_to_arg(['--ignore_fields', '-ign']).split()
        args.group_fields = str_to_arg(['--group_fields', '-grp']).split()
        args.variant = str_to_arg(['--variant', '-var'])
        
        num_processes = self.m_spinCtrl_np.GetValue() # Parallels process scrapping.
        args.retries = self.m_spinCtrl_retries.GetValue() # Retry time in the scraps.
        args.throttling_delay = self.m_spinCtrlDouble_throttling.GetValue() # Delay between consecutive scrapes.
        args.collapse_refs = self.m_checkBox_collapseRefs.GetValue() # Collapse refs in the spreadsheet.
        
        if self.m_listBox_edatool.GetStringSelection():
            for k,v in eda_tool_dict.items():
               if v['label']==self.m_listBox_edatool.GetStringSelection():
                  eda_module = v['module']
                  break
        args.eda_tool = eda_module
        
        # Get the current distributors to scrape.
        choisen_dist = list(self.m_checkList_dist.GetCheckedItems())
        if choisen_dist:
            dist_list = []
            #choisen_dist = [self.m_checkList_dist.GetString(idx) for idx in choisen_dist]
            for idx in choisen_dist:
                label = self.m_checkList_dist.GetString(idx)
                for k,v in distributor_dict.items():
                    if v['label']==label:
                        dist_list.append( v['module'] )
                        break
        else:
            dist_list = None
        args.include = dist_list
        
        # Run KiCost main function and print in the log the elapsed time.
        start_time = time.time()
        try:
            kicost(in_file=args.input, eda_tool_name=args.eda_tool,
                out_filename=args.output, collapse_refs=args.collapse_refs,
                user_fields=args.fields, ignore_fields=args.ignore_fields,
                group_fields=args.group_fields, variant=args.variant,
                dist_list=args.include, num_processes=num_processes,
                scrape_retries=args.retries, throttling_delay=args.throttling_delay)
            if self.m_checkBox_openXLS.GetValue():
                print('Opening the output file \'{}\'...'.format(
                                    os.path.basename(spreadsheet_file)
                                )
                            )
                open_file(spreadsheet_file)
        except Exception as e:
            print(e)
        print('Elapsed time: {} seconds'.format(time.time() - start_time) )
        #self.m_gauge_process.SetValue(100)
        
        return

    #----------------------------------------------------------------------
    def runTerminal( self ):
        ''' @brief Run KiCost in CLI interface using the GUI settings.'''
        
        # Get the current distributors to scrape.
        choisen_dist = list(self.m_checkList_dist.GetCheckedItems())
        if choisen_dist:
            dist_list = ' --include'
            #choisen_dist = [self.m_checkList_dist.GetString(idx) for idx in choisen_dist]
            for idx in choisen_dist:
                label = self.m_checkList_dist.GetString(idx)
                for k,v in distributor_dict.items():
                    if v['label']==label:
                        dist_list += ' ' + v['module']
                        break
            #choisen_dist = ' --include ' + ' '.join(choisen_dist)
        else:
            dist_list = ''
        
        command = ("kicost"
            + " --input " + ' '.join(['"'+fileN+'"' for fileN in re.split(SEP_FILES, self.m_comboBox_files.GetValue())])
            + " --num_processes " + str(self.m_spinCtrl_np.GetValue()) # Parallels process scrapping.
            + " --retries " + str(self.m_spinCtrl_retries.GetValue()) # Retry time in the scraps.
            + " --throttling " + str(self.m_spinCtrlDouble_throttling.GetValue()) # Delay between consecutive scrapes.
            + " --overwrite" * self.m_checkBox_overwrite.GetValue()
            + " --no_collpase" * ( not self.m_checkBox_collapseRefs.GetValue() )
            + (" --debug " + str(self.m_spinCtrl_debugLvl.GetValue()) if self.m_spinCtrl_debugLvl.GetValue() > 0 else "") # Degub level opiton.
            + " --quiet" * self.m_checkBox_quite.GetValue()
            + dist_list
            )
        
        if self.m_listBox_edatool.GetStringSelection():
            for k,v in eda_tool_dict.items():
               if v['label']==self.m_listBox_edatool.GetStringSelection():
                  eda_module = v['module']
                  break
            command += " -eda " + eda_module
        
        if self.m_textCtrlextracmd.GetValue():
            command += ' ' + self.m_textCtrlextracmd.GetValue()
        
        if self.m_checkBox_openXLS.GetValue():
            spreadsheet_file = re.split(SEP_FILES, self.m_comboBox_files.GetValue())
            if len(spreadsheet_file)==1:
                spreadsheet_file = os.path.splitext( spreadsheet_file[0] )[0] + '.xlsx'
            else:
                spreadsheet_file = output_filename_multipleinputs( spreadsheet_file )
            
            if platform.system()=='Linux':
                command += ' && xdg-open ' + '"' + spreadsheet_file + '"'
            elif platform.system()=='Windows':
                command += ' && explorer ' + '"' + spreadsheet_file + '"'
            elif platform.system()=='Darwin': # Mac-OS
                command += ' && open -n ' + '"' + spreadsheet_file + '"'
            else:
                print('Not recognized OS.')
        
        command += '&' # Run as other process.
        print("Running: ", command)
        subprocess.call(command, shell=True) # `os.system`not accept the "&&"

    #----------------------------------------------------------------------
    def set_properties(self):
        ''' @brief Set the current proprieties of the graphical elements.'''
        actualDir = os.path.dirname(os.path.abspath(__file__)) # Application dir.
        
        # Set the aplication windows title and configurations
        self.SetTitle('KiCost v.' + __version__)
        self.SetIcon(wx.Icon(actualDir + os.sep + 'kicost.ico', wx.BITMAP_TYPE_ICO))
        
        # Current distrubutors module recognized.
        distributors_list = sorted( [ distributor_dict[d]['label'] for d in distributor_dict.keys() ] )
        self.m_checkList_dist.Clear()
        self.m_checkList_dist.Append(distributors_list)
        for idx in range(len(distributors_list)):
            self.m_checkList_dist.Check(idx,True) # All start checked (after is modifed by the configuration file).
        
        # Current EDA tools module recognized.
        eda_names = sorted( [ eda_tool_dict[eda]['label'] for eda in eda_tool_dict.keys() ] )
        self.m_listBox_edatool.Clear()
        self.m_listBox_edatool.Append(eda_names)
        
        # Credits and other informations, search by `AUTHOR.rst` file.
        self.m_staticText_version.SetLabel( 'KiCost version ' + __version__ )
        self.m_bitmap_icon.SetIcon(wx.Icon(actualDir + os.sep + 'kicost.ico', wx.BITMAP_TYPE_ICO))
        try:
            credits_file = open(actualDir + os.sep+'..'+os.sep + 'kicost-' + __version__ + '.egg-info' + os.sep + 'AUTHOR.rst')
            credits = credits_file.read()
            credits_file.close()
        except:
            credits = r'''=======
            Credits
            =======
            Development Lead
            ----------------
            * XESS Corporation <info@xess.com>
            Contributors
            ------------
            * Oliver Martin: https://github.com/oliviermartin
            * Timo Alho: https://github.com/timoalho
            * Steven Johnson: https://github.com/stevenj
            * Diorcet Yann: https://github.com/diorcety
            * Giacinto Luigi Cerone https://github.com/glcerone
            * Hildo Guillardi Júnior https://github.com/hildogjr
            * Adam Heinrich https://github.com/adamheinrich
            ------------
            GUI by Hildo Guillardi Júnior
            '''
            credits = re.sub(r'\n[\t ]+', '\n', credits)  # Remove leading whitespace
        self.m_staticText_credits.SetLabel(credits)
        
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
                '''Convert a string tuple into a  wxPoint'''
                p = re.findall('\d+', s)
                return wx.Point(int(p[0]), int(p[1]))
            def str_to_wxsize(s):
                '''Convert a string tuple into a  wxRect'''
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
                
                try:
                    # Find the wxPython element handle to access the methods.
                    wxElement_handle = self.__dict__[entry]
                    # Each wxPython object have a specific parameter value
                    # to be saved and restored in the software initialization.
                    if isinstance(wxElement_handle, wx._core.TextCtrl):
                        wxElement_handle.SetValue( entry_value )
                    elif isinstance(wxElement_handle, wx._core.CheckBox):
                        wxElement_handle.SetValue( (True if entry_value=='True' else False) )
                    elif isinstance(wxElement_handle, wx._core.CheckListBox):
                        value = re.split(',', entry_value )
                        for idx in range(wxElement_handle.GetCount()): # Reset all checked.
                            wxElement_handle.Check(idx, False)
                        for dist_checked in value: # Check only the founded names.
                            idx = wxElement_handle.FindString( dist_checked )
                            if idx!=wx.NOT_FOUND:
                                wxElement_handle.Check(idx, True)
                    elif isinstance(wxElement_handle, wx._core.SpinCtrl):
                        wxElement_handle.SetValue( int(entry_value) )
                    elif isinstance(wxElement_handle, wx._core.SpinCtrlDouble):
                        wxElement_handle.SetValue( float(entry_value) )
                    elif isinstance(wxElement_handle, wx._core.ComboBox):
                        value = re.split(',', entry_value)
                        for element in value:
                            if element:
                                wxElement_handle.Append( element )
                    elif isinstance(wxElement_handle, wx._core.ListBox):
                        wxElement_handle.SetSelection( wxElement_handle.FindString( entry_value ) )
                    elif isinstance(wxElement_handle, wx._core.Notebook):
                        wxElement_handle.SetSelection( int(entry_value) )
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
            self.m_textCtrl_messages.AppendText('Configurations not recovered: <'+str(e)+'>.')

    #----------------------------------------------------------------------
    def save_properties(self):
        ''' @brief Save the current proprieties of the graphical elements.'''
        try:
            configHandle = wx.Config(CONFIG_FILE)
            
            # Save position and size.
            configHandle.Write(GUI_POSITION_ENTRY, str(self.GetPosition()))
            configHandle.Write(GUI_SIZE_ENTRY, str(self.GetSize()))
            
            # Sweep all elements in `self()` to find the grafical ones
            # instance of the wxPython and salve the specific configuration.
            for wxElement_name, wxElement_handle in self.__dict__.items():
                try:
                    # Each wxPython object have a specific parameter value
                    # to be saved and restored in the software initialization.
                    if isinstance(wxElement_handle, wx._core.TextCtrl) and wxElement_name != 'm_textCtrl_messages':
                        # Save each TextCtrl (TextBox) that is not the status messages.
                        configHandle.Write(wxElement_name, wxElement_handle.GetValue() )
                    elif isinstance(wxElement_handle, wx._core.CheckBox):
                        configHandle.Write(wxElement_name, ('True' if wxElement_handle.GetValue() else 'False') )
                    elif isinstance(wxElement_handle, wx._core.CheckListBox):
                        value = [wxElement_handle.GetString(idx) for idx in wxElement_handle.GetCheckedItems()]
                        configHandle.Write(wxElement_name, ','.join(value) )
                    elif isinstance(wxElement_handle, wx._core.SpinCtrl) or isinstance(wxElement_handle, wx._core.SpinCtrlDouble):
                        configHandle.Write(wxElement_name, str(wxElement_handle.GetValue()) )
                    elif isinstance(wxElement_handle, wx._core.ComboBox):
                        value = [wxElement_handle.GetString(idx) for idx in range(wxElement_handle.GetCount())]
                        configHandle.Write(wxElement_name, ','.join(value) )
                    elif isinstance(wxElement_handle, wx._core.ListBox):
                        configHandle.Write(wxElement_name, wxElement_handle.GetStringSelection() )
                    elif isinstance(wxElement_handle, wx._core.Notebook):
                        configHandle.Write(wxElement_name, str(wxElement_handle.GetSelection()) )
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
            self.m_textCtrl_messages.AppendText('Configurations not saved: <'+str(e)+'>.')





#######################################################################

def kicost_gui():
    ''' @brief Load the graphical interface.'''
    app = wx.App(redirect=False)
    frame = formKiCost(None)
    frame.Show()
    app.MainLoop()

def kicost_gui_run(fileName):
    ''' @brief Execute the `fileName`under KiCost loading the graphical interface.
        @param LIst of the file name.
    '''
    app = wx.App(redirect=False)
    frame = formKiCost(None)
#    frame.Show()
    frame.m_comboBox_files.SetValue('"' + '", "'.join(fileName) + '"')
    frame.updateEDAselection()
    frame.runTerminal()
#    app.MainLoop()
