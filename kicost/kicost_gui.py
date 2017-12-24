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
import os
from . import __version__ # Version control by @xesscorp.
from .kicost import distributors, eda_tools # List of the distributos and EDA supported.

__all__ = ['kicost_gui']


# Author information.
__author__ = 'Hildo Guillardi Junior'
__webpage__ = 'https://github.com/hildogjr/'
__company__ = 'University of Campinas - Brazil'


WILDCARD = "BoM compatible formatc (*.xml,*.csv)|*.xml;*.csv|"\
			"KiCad/Altium BoM file (*.xml)|*.xml|" \
			"Proteus/Generic BoM file (*.csv)|*.csv"

class MyForm(wx.Frame):
	#----------------------------------------------------------------------
	def __init__(self):
		wx.Frame.__init__(self, None, wx.ID_ANY, "KiCost v"+__version__)
		panel = wx.Panel(self, wx.ID_ANY)
		self.currentDirectory = os.getcwd()

		# Select file button.
		openFileDlgBtn = wx.Button(panel, label="Open BoM files")
		openFileDlgBtn.Bind(wx.EVT_BUTTON, self.onOpenFile)
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(openFileDlgBtn, 0, wx.ALIGN_RIGHT, 5) # Put the buttons in a sizer.
		
		# Create a check box to each distributor.
		distributorsList = [*sorted(list(distributors.keys()))]
		for dist in distributorsList:
			print(dist)
			#distCheck = wx.CheckBox(panel, label=dist, pos=wx.Point(40, 150))
			#sizer.Add(distCheck, 0, wx.ALL|wx.CENTER, 5)
		
		# Create a combox with the file recognized formats (EDA tools).
		#print('EDA list:', *sorted(list(eda_tools.keys())))
#		edaComboBox = wx.ComboBox(self, -1, value='dsadas', pos=wx.Point(40, 130),
#			size=wx.Size(100, 42), choices=['1','2'])
		#sizer.Add(edaComboBox, 0, wx.ALL|wx.CENTER, 5)
		
		panel.SetSizer(sizer)

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
		dlg.Destroy()





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
