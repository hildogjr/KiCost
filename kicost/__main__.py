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

# Inserted by Pasteurize tool.
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from builtins import open
from future import standard_library
standard_library.install_aliases()

import argparse as ap # Command argument parser.
import os
import sys
import logging
import time
#import inspect # To get the internal module and informations of a module/class.
from .kicost import kicost # kicost core functions.
try:
    from .kicost_gui import * # User guide.
except ImportError:
    pass # If the wxPython dependences are not installed and
         # the user just want the KiCost CLI.
from .distributors import distributors
from .eda_tools import eda_tool #from . import eda_tools as eda_tools_imports
from . import __version__ # Version control by @xesscorp.

NUM_PROCESSES = 30  # Maximum number of parallel web-scraping processes..
HTML_RESPONSE_RETRIES = 2 # Number of attempts to retrieve part data from a website.

logger = logging.getLogger('kicost')

###############################################################################
# Command-line interface.
###############################################################################

def main():

    parser = ap.ArgumentParser(
        description='Build cost spreadsheet for a KiCAD project.')
    parser.add_argument('-v', '--version',
                        action='version',
                        version='KiCost ' + __version__)
    parser.add_argument('-i', '--input',
                        nargs='+',
                        type=str,
                        metavar='file.xml',
                        help='One or more schematic BOM XML files.')
    parser.add_argument('-o', '--output',
                        nargs='?',
                        type=str,
                        metavar='file.xlsx',
                        help='Generated cost spreadsheet.')
    parser.add_argument('-f', '--fields',
                        nargs='+',
                        type=str,
                        default=[],
                        metavar='name',
                        help='''Specify the names of additional part fields to 
                            extract and insert in the global data section of 
                            the spreadsheet.''')
    parser.add_argument('-var', '--variant',
                        nargs='+',
                        type=str,
                        default=' ', # Default variant is a space.
                        help='schematic variant name filter.')
    parser.add_argument('-w', '--overwrite',
                        action='store_true',
                        help='Allow overwriting of an existing spreadsheet.')
    parser.add_argument('-s', '--serial',
                        action='store_true',
                        help='Do web scraping of part data using a single process.')
    parser.add_argument('-q', '--quiet',
                        action='store_true',
                        help='Enable quiet mode with no warnings.')
    parser.add_argument('-np', '--num_processes',
                        nargs='?',
                        type=int,
                        default=NUM_PROCESSES,
                        const=NUM_PROCESSES,
                        metavar='NUM_PROCESSES',
                        help='''Set the number of parallel 
                            processes used for web scraping part data.''')
    parser.add_argument('-ign', '--ignore_fields',
                        nargs='+',
                        default=[],
                        help='Declare part fields to ignore when grouping parts.',
                        metavar='name',
                        type=str)
    parser.add_argument('-d', '--debug',
                        nargs='?',
                        type=int,
                        default=None,
                        metavar='LEVEL',
                        help='Print debugging info. (Larger LEVEL means more info.)')
    parser.add_argument('-eda', '--eda_tool', choices=['kicad', 'altium', 'csv'],
                        nargs='+',
                        default='kicad',
                        help='Choose EDA tool from which the XML BOM file originated, or use csv for .CSV files.')
    parser.add_argument('--show_dist_list',
                        action='store_true',
                        help='Show list of distributors that can be scraped for cost data, then exit.')
    parser.add_argument('--show_eda_list',
                        action='store_true',
                        help='Show list of eda softwares that KiCost can read, then exit.')
    parser.add_argument('-e', '--exclude',
                        nargs='+', type=str, default='',
                        metavar = 'dist',
                        help='Excludes the given distributor(s) from the scraping process.')
    parser.add_argument('--include',
                        nargs='+', type=str, default='',
                        metavar = 'dist',
                        help='Includes only the given distributor(s) in the scraping process.')
    parser.add_argument('-rt', '--retries',
                        nargs='?',
                        type=int,
                        default=HTML_RESPONSE_RETRIES,
                        metavar = 'num_retries',
                        help='Specify the number of attempts to retrieve part data from a website.')
    parser.add_argument('--user',
                        action='store_true',
                        help='Start the user guide to run KiCost passing the file parameter give by "--input", all others parameters are ignored.')


    args = parser.parse_args()

    # Set up logging.
    if args.debug is not None:
        log_level = logging.DEBUG + 1 - args.debug
    elif args.quiet is True:
        log_level = logging.ERROR
    else:
        log_level = logging.WARNING
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    logger.addHandler(handler)
    logger.setLevel(log_level)

    if args.show_dist_list:
        print('Distributor list:', *sorted(list(distributors.keys())))
        return
    if args.show_eda_list:
        #eda_names = [o[0] for o in inspect.getmembers(eda_tools_imports) if inspect.ismodule(o[1])]
        #print('EDA supported list:', ', '.join(eda_names))
        print('EDA supported list:', *sorted(list(eda_tool.keys())))
        return

    # Set up spreadsheet output file.
    if args.output == None:
        # If no output file is given...
        if args.input != None:
            # Send output to spreadsheet with name of input file.
            if len(args.input)>1:
                # Compose a name with the multiple BOM input file names,
                # limiting to the first 5 caracheters of each name (avoid
                # huge names). This is dynamic if the number of input
                # files passed.
                args.output = '-'.join( [ os.path.splitext(args.input[i][:max(int(20/len(args.input)),5)])[0] for i in range(len(args.input))] ) + '.xlsx'
            else:
                args.output = os.path.splitext(args.input[0])[0] + '.xlsx'
        else:
            # Send output to spreadsheet with name of this application.
            args.output = os.path.splitext(sys.argv[0])[0] + '.xlsx'
    else:
        # Output file was given. Make sure it has spreadsheet extension.
        args.output = os.path.splitext(args.output)[0] + '.xlsx'

    # Call the KiCost interface to alredy run KiCost, this is just to use the
    # saved user configurations of the graphical interface.
    if args.user:
        try:
            kicost_gui_run([os.path.abspath(fileName) for fileName in args.input])
        except NameError:
            kicost_gui_notdependences()
            #kicost_gui_run([os.path.abspath(fileName) for fileName in args.input])
        return

    # Handle case where output is going into an existing spreadsheet file.
    if os.path.isfile(args.output):
        if not args.overwrite:
            logger.critical('''Output file {} already exists! Use the
                --overwrite option to replace it.'''.format(args.output))
            sys.exit(1)

    # Set XML input source.
    if args.input == None:
        try:
            kicost_gui() # Use the user guide.
        except NameError:
            kicost_gui_notdependences()
            #kicost_gui()
        return
    else:
        # Otherwise get XML from the given file.
        for i in range(len(args.input)):
            # Set '.xml' as the default file extension, treating this exception
            # allow other files extension and formats.
            try:
                if os.path.splitext(args.input[i])[1] == '':
                    args.input[i] += '.xml'
                elif os.path.splitext(args.input[i])[1] == '.csv' or args.eda_tool[i] == 'csv':
                    args.eda_tool = 'csv'
            except IndexError:
                pass

    # Set number of processes to use for web scraping.
    if args.serial:
        num_processes = 1
    else:
        num_processes = args.num_processes

    kicost(in_file=args.input, out_filename=args.output,
        user_fields=args.fields, ignore_fields=args.ignore_fields, 
        variant=args.variant, num_processes=num_processes, eda_tool_name=args.eda_tool,
        exclude_dist_list=args.exclude, include_dist_list=args.include,
        scrape_retries=args.retries)

###############################################################################
# Main entrypoint.
###############################################################################
if __name__ == '__main__':
    start_time = time.time()
    main()
    logger = logging.getLogger('kicost')
    logger.log(logging.DEBUG-2, 'Elapsed time: %f seconds', time.time() - start_time)


###############################################################################
# Additional functions
###############################################################################

def kicost_gui_notdependences():
    print('You don\'t have the wxPython dependence to run the GUI interface. Run once of the follow commands in terminal to install them:')
    print('pip install wxPython # For python 2.5')
    print('pip3 install wxPython # For python 3.0+')
    print('Or download from last version from <https://wxpython.org/>')
    sys.exit(1)
