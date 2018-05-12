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
import os, sys, platform
import logging, time
#import inspect # To get the internal module and informations of a module/class.
from .kicost import * # kicost core functions.
try:
    from .kicost_gui import * # User guide.
except ImportError:
    pass # If the wxPython dependences are not installed and
         # the user just want the KiCost CLI.
from .distributors import distributor_dict
from .eda_tools import eda_tool_dict
from . import __version__ # Version control by @xesscorp.

NUM_PROCESSES = 30  # Maximum number of parallel web-scraping processes.
HTML_RESPONSE_RETRIES = 2 # Number of attempts to retrieve part data from a website.

from .globals import *
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
                        metavar='FILE.XML',
                        help='One or more schematic BOM XML files.')
    parser.add_argument('-o', '--output',
                        nargs='?',
                        type=str,
                        metavar='FILE.XLSX',
                        help='Generated cost spreadsheet.')
    parser.add_argument('-f', '--fields',
                        nargs='+',
                        type=str,
                        default=[],
                        metavar='NAME',
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
                        help='Declare part fields to ignore when reading the BoM file.',
                        metavar='NAME',
                        type=str)
    parser.add_argument('-grp', '--group_fields',
                        nargs='+',
                        default=[],
                        help='Declare part fields to merge when grouping parts.',
                        metavar='NAME',
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
                        help='Show list of EDA tools whose files KiCost can read, then exit.')
    parser.add_argument('--no_collapse',
                        action='store_true',
                        help='Do not collapse the part references in the spreadsheet.')
    parser.add_argument('-e', '--exclude',
                        nargs='+', type=str, default='',
                        metavar = 'DIST',
                        help='Excludes the given distributor(s) from the scraping process.')
    parser.add_argument('--include',
                        nargs='+', type=str, default='',
                        metavar = 'DIST',
                        help='Includes only the given distributor(s) in the scraping process.')
    parser.add_argument('--no_scrape',
                        action='store_true',
                        help='Create a spreadsheet without scraping part data from distributor websites.')
    parser.add_argument('-rt', '--retries',
                        nargs='?',
                        type=int,
                        default=HTML_RESPONSE_RETRIES,
                        metavar = 'NUM_RETRIES',
                        help='Specify the number of attempts to retrieve part data from a website.')
    parser.add_argument('--throttling_delay',
                        nargs='?', type=float, default=0.0,
                        metavar='DELAY',
                        help="Specify minimum delay (in seconds) between successive accesses to a distributor's website.")
    parser.add_argument('--currency', '--locale',
                        nargs='?',
                        type=str,
                        default='USD',
                        help='Define the priority locale/country and currency on the scrape. Use the ISO4217 for currency and ISO3166:2 for country. Input e.g.: `US`, `USD`, `US-USD` or `EUR-US`. Currency is priritized over the locale/country. If give country with more than one currency, it will be chosen, in the sequence, `USD`, `EUR` or alphabetical order. Default: `USD`.')
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
    #handler = logging.StreamHandler(sys.stdout)
    #handler.setLevel(log_level)
    #logger.addHandler(handler) # It's not necessary to add a handle here, the default is already `sys.stdout` and adding twice it creates the BUG #193, doesn't allowing to use correctly the `tqdm` (process bar) print handle.
    logger.setLevel(log_level)

    if args.show_dist_list:
        print('Distributor list:', *sorted(list(distributor_dict.keys())))
        return
    if args.show_eda_list:
        #eda_names = [o[0] for o in inspect.getmembers(eda_tools_imports) if inspect.ismodule(o[1])]
        #print('EDA supported list:', ', '.join(eda_names))
        print('EDA supported list:', *sorted(list(eda_tool_dict.keys())))
        return

    # Set up spreadsheet output file.
    if args.output == None:
        # If no output file is given...
        if args.input != None:
            # Send output to spreadsheet with name of input file.
            if len(args.input)>1:
                # Compose a name with the multiple BOM input file names.
                args.output = output_filename_multipleinputs(args.input)
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
        except (ImportError,NameError):
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
        except (ImportError,NameError):
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

    # Remove all the distributor from the list for not scrape any web site.
    if args.no_scrape:
        dist_list = None
    else:
        if not args.include:
            dist_list = list(distributor_dict.keys())
        else:
            dist_list = args.include
        for d in args.exclude:
            dist_list.remove(d)

    logger.log(DEBUG_OBSESSIVE, 'Started KiCost v.{} on {}({}) Python {}.{}.{}'.format(
                                              __version__,
                                              platform.platform(),
                                              platform.architecture()[0],
                                              sys.version_info.major,
                                              sys.version_info.minor,
                                              sys.version_info.micro)
                                          )
    #try:
    kicost(in_file=args.input, eda_tool_name=args.eda_tool,
        out_filename=args.output, collapse_refs=not args.no_collapse,
        user_fields=args.fields, ignore_fields=args.ignore_fields,
        group_fields=args.group_fields, variant=args.variant,
        dist_list=dist_list, num_processes=num_processes,
        scrape_retries=args.retries, throttling_delay=args.throttling_delay,
        local_currency=args.currency)
    #except Exception as e:
    #    sys.exit(e)

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
    print('pip3 install -U wxPython # For Windows & macOS')

    print('pip install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-16.04 wxPython # For Linux 16.04')
    print('Or download from last version from <https://wxpython.org/pages/downloads/>')
    sys.exit(1)
