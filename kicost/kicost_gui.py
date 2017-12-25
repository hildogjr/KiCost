# -*- coding: utf-8 -*- 
# MIT license
#
# Copyright (C) 2018 by XESS Corporation / Hildo G Jr
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

# Libraries.
import wx # wxWidgets for Python.
import os # To access OS commands.
import platform # To check the system platform when open the XLS file.
import re # Regular expression parser.
from . import __version__ # Version control by @xesscorp.
from .kicost import distributors, eda_tools # List of the distributos and EDA supported.

__all__ = ['kicost_gui']


# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'


WILDCARD = "BoM compatible formats (*.xml,*.csv)|*.xml;*.csv|"\
			"KiCad/Altium BoM file (*.xml)|*.xml|" \
			"Proteus/Generic BoM file (*.csv)|*.csv"

class MyForm(wx.Frame):
	#----------------------------------------------------------------------
	def __init__(self):
		wx.Frame.__init__(self, None, wx.ID_ANY, "KiCost v" + __version__)
		self.Bind(wx.EVT_CLOSE, self._when_closed)
		
		self.currentDirectory = os.getcwd()
		
		self.notebook_1 = wx.Notebook(self, wx.ID_ANY)
		
		
		## First tab.
		self.notebook_1_pane_1 = wx.Panel(self.notebook_1, wx.ID_ANY)
		self.combobox_files = wx.ComboBox(self.notebook_1_pane_1, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
		
		self.button_openFile = wx.Button(self.notebook_1_pane_1, wx.ID_ANY, "Open BOM")
		self.button_openFile.Bind(wx.EVT_BUTTON, self.onOpenFile)
		
		# Create a check box to each distributor.
		self.distributors_list = [*sorted(list(distributors.keys()))]
		self.checklistbox_dist = wx.CheckListBox(self.notebook_1_pane_1, wx.ID_ANY, choices=self.distributors_list)
		
		#self.eda_list = [*sorted(list(eda_tools.keys()))]
		#for eda in self.eda_list:
		#	print(eda)
		self.listbox_eda = wx.ListBox(self.notebook_1_pane_1, wx.ID_ANY, choices=["nada"])
		
		self.button_run = wx.Button(self.notebook_1_pane_1, wx.ID_ANY, "KiCost it!")
		self.button_run.Bind(wx.EVT_BUTTON, self.run)
		self.checkbox_openspreadsheet = wx.CheckBox(self.notebook_1_pane_1, wx.ID_ANY, "Open XLSX at the end")
		
		
		## Second tab.
		self.notebook_1_pane_2 = wx.Panel(self.notebook_1, wx.ID_ANY)
		self.label_2 = wx.StaticText(self.notebook_1_pane_2, wx.ID_ANY, "Parallels process")
		self.label_3 = wx.StaticText(self.notebook_1_pane_2, wx.ID_ANY, "Scrap retries")
		self.spinctrl_np = wx.SpinCtrl(self.notebook_1_pane_2, wx.ID_ANY, "", min=1, max=30)
		self.spinctrl_retries = wx.SpinCtrl(self.notebook_1_pane_2, wx.ID_ANY, "", min=4, max=100)
		self.checkbox_overwrite = wx.CheckBox(self.notebook_1_pane_2, wx.ID_ANY, "--overwrite")
		self.checkbox_quiet = wx.CheckBox(self.notebook_1_pane_2, wx.ID_ANY, "--quiet")
		
		
		## Thirth tab.
		self.notebook_1_pane_3 = wx.Panel(self.notebook_1, wx.ID_ANY)
		
		try:
			credits_file = open(self.currentDirectory + '/../kicost-' + __version__ + '.dist-info/AUTHOR.rst')
			credits = credits_file.read()
			credits_file.close()
		except:
			credits = '''
			=======
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
			'''
			credits = re.sub('\t*','',credits)
		
		self.label_1 = wx.StaticText(self.notebook_1_pane_3, wx.ID_ANY, 
			'KiCost version ' + __version__ + '\n\n'
			+ credits # This text above have to be dinamic replaced by `AUTHOR.rst`.
			+ '\nGraphical interface by Hildo G Jr')
		
		self.__set_properties()
		self.__do_layout()
		# end wxGlade


	#----------------------------------------------------------------------
	def _when_closed(self, event):
		''' When the application is closed '''
		self.__save_properties() # Save the current configuration before close.
		#self.Close()
		self.Destroy()


	#----------------------------------------------------------------------
	def onOpenFile(self, event):
		""" Create and show the Open FileDialog """
		dlg = wx.FileDialog(
			self, message="Select BoMs",
			defaultDir=self.currentDirectory, 
			defaultFile="",
			wildcard=WILDCARD,
			style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR
			)
		if dlg.ShowModal() == wx.ID_OK:
			paths = dlg.GetPaths()
			print("You chose the following file(s):")
			for path in paths:
				print(path)
			self.combobox_files.SetValue( ' '.join(['"' + file + '"' for file in paths]) )
		dlg.Destroy()


	#----------------------------------------------------------------------
	def run(self, event):
		''' Run KiCost '''
		
		self.__save_properties() # Save the current graphical configuration before call the KiCost motor.
		
		choisen_dist = list(self.checklistbox_dist.GetCheckedItems())
		if choisen_dist:
			choisen_dist = [self.distributors_list[idx] for idx in choisen_dist]
			choisen_dist = ' --include ' + ' '.join(choisen_dist)
		else:
			choisen_dist = ''
		
		command = ("kicost"
			+ " -i " + self.combobox_files.GetValue()
			+ " -np " + str(self.spinctrl_np.GetValue()) # Parallels process scrapping.
			+ " -rt " + str(self.spinctrl_retries.GetValue()) # Retry time in the scraps
			+ " -w" * self.checkbox_overwrite.GetValue()
			+ " -q" * self.checkbox_quiet.GetValue()
			+ choisen_dist
			)
		print("Running: ", command)
		os.system(command) # Could call directly the `kicost.py`, which is better? Missing put the process bar here!
		
		if self.checkbox_openspreadsheet.GetValue():
			spreadsheet_file = os.path.splitext( self.combobox_files.GetValue() ) + '.xlsx'
			print('Opening output file: ', spreadsheet_file)
			if platform.system()=='Linux':
				os.system('xdg-open ' + '"' + spreadsheet_file + '"')
			elif platform.system()=='Windows':
				print('Do know the Windows command')
			elif platform.system()=='Darwin':
				print('Do know the MAC-OS command')
			else: # Not tested
				print('Not recognized OS.')



	#----------------------------------------------------------------------
	def __set_properties(self):
		''' Set the initial proprieties of the graphical elements '''
		# begin wxGlade: MyFrame.__set_properties
		self.checklistbox_dist.SetSelection(0)
		self.listbox_eda.SetSelection(0)
		self.checkbox_overwrite.SetValue(1)
		self.checkbox_quiet.SetValue(1)
		# end wxGlade


	#----------------------------------------------------------------------
	def __save_properties(self):
		''' Save the current proprieties of the graphical elements '''


	#----------------------------------------------------------------------
	def __do_layout(self):
		''' Place the graphical components in the correct place '''
		# begin wxGlade: MyFrame.__do_layout
		sizer_1 = wx.BoxSizer(wx.VERTICAL)
		sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
		grid_sizer_1 = wx.GridSizer(3, 2, 0, 1)
		sizer_3 = wx.BoxSizer(wx.VERTICAL)
		sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
		sizer_6 = wx.BoxSizer(wx.VERTICAL)
		sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
		sizer_4.Add(self.combobox_files, 0, wx.FIXED_MINSIZE, 0)
		sizer_4.Add(self.button_openFile, 0, 0, 0)
		sizer_3.Add(sizer_4, 1, 0, 0)
		sizer_5.Add(self.checklistbox_dist, 0, wx.EXPAND, 0)
		sizer_6.Add(self.listbox_eda, 0, wx.EXPAND, 0)
		sizer_6.Add(self.button_run, 0, 0, 0)
		sizer_6.Add(self.checkbox_openspreadsheet, 0, 0, 0)
		sizer_5.Add(sizer_6, 1, 0, 0)
		sizer_3.Add(sizer_5, 1, 0, 0)
		self.notebook_1_pane_1.SetSizer(sizer_3)
		grid_sizer_1.Add(self.label_2, 0, 0, 0)
		grid_sizer_1.Add(self.label_3, 0, 0, 0)
		grid_sizer_1.Add(self.spinctrl_np, 0, 0, 0)
		grid_sizer_1.Add(self.spinctrl_retries, 0, 0, 0)
		grid_sizer_1.Add(self.checkbox_overwrite, 0, 0, 0)
		grid_sizer_1.Add(self.checkbox_quiet, 0, 0, 0)
		self.notebook_1_pane_2.SetSizer(grid_sizer_1)
		sizer_2.Add(self.label_1, 0, wx.ALIGN_CENTER | wx.EXPAND, 0)
		self.notebook_1_pane_3.SetSizer(sizer_2)
		self.notebook_1.AddPage(self.notebook_1_pane_1, "BoM")
		self.notebook_1.AddPage(self.notebook_1_pane_2, "Config")
		self.notebook_1.AddPage(self.notebook_1_pane_3, "About")
		sizer_1.Add(self.notebook_1, 1, wx.ALIGN_CENTER | wx.EXPAND, 0)
		self.SetSizer(sizer_1)
		sizer_1.Fit(self)
		self.Layout()
		# end wxGlade





#######################################################################

def kicost_gui():
	app = wx.App(redirect=False)
	frame = MyForm()
	frame.Show()
	app.MainLoop()
	
	
	#kicost(in_file=args.input, out_filename=args.output,
#		user_fields=args.fields, ignore_fields=args.ignore_fields, 
#		variant=args.variant, num_processes=num_processes, eda_tool_name=args.eda_tool,
#		exclude_dist_list=args.exclude, include_dist_list=args.include,
#		scrape_retries=args.retries)
