try:
    import wx # wxWidgets for Python.
except ImportError:
    raise wxPythonNotPresent()


#======================================================================
class formKiCost_raw(wx.Frame):
    def __init__(self, parent):
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

        self.m_checkBox_XLSXtoODS = wx.CheckBox(self.m_panel1, wx.ID_ANY, u"Convert to ODS", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_checkBox_XLSXtoODS.SetValue(False)
        self.m_checkBox_XLSXtoODS.SetToolTip(wx.ToolTip(u"Convert the file output to ODS format quietly."))
        self.m_checkBox_XLSXtoODS.Bind(wx.EVT_CHECKBOX, self.updateOutputFilename)
        bSizer6.Add(self.m_checkBox_XLSXtoODS, 0, wx.ALL, 5)
        self.m_checkBox_XLSXtoODS.Enable(False)

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

        self.m_bitmap_icon = wx.StaticBitmap(self.m_panel3, wx.ID_ANY, wx.NullBitmap, wx.DefaultPosition, wx.Size(200,100),0)
        self.m_bitmap_icon.SetIcon(wx.Icon(actualDir + os.sep + 'kicost.ico', wx.BITMAP_TYPE_ICO))
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

        self.m_bitmap_icon = wx.StaticBitmap(self.m_panel3, wx.ID_ANY, wx.NullBitmap, wx.DefaultPosition, wx.Size(200,100),0)
        self.m_bitmap_icon.SetIcon(wx.Icon(actualDir + os.sep + 'kitspace.png', wx.BITMAP_TYPE_PNG))
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

    def __del__(self):
        pass

    def app_close(self, event):
        pass

    def open_webpage_click(self, event):
        pass
    def open_issuepage_click(self, event):
        pass
    def open_updatepage_click(self, event):
        pass
    def open_powered_by(self, event):
        pass

    def check_updates_click(self, event):
        pass

    '''Pop-up menus on main tab.'''
    def m_textCtrl_messages_rClick(self, event):
        pass
    def m_textCtrl_distributors_rClick(self, event):
        pass

    def m_comboBox_files_selecthist(self, event):
        pass

    def updateOutputFilename(self, event=None):
        pass

    def updateEDAselection(self):
        pass

    def button_openfile(self, event):
        pass

    def button_saveas(self, event):
        pass

    def button_run(self, event):
        pass
