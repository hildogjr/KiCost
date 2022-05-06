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

# Libraries.
import argparse as ap  # Command argument parser.
import os
import sys
import platform
import time
import tqdm
import logging
import subprocess
# Debug, language and default configurations.
from .global_vars import wxPythonNotPresent, DEF_MAX_COLUMN_W, W_CMDLINE
# Sub systems can be imported before logger
from .edas import get_registered_eda_names, set_edas_logger  # noqa: E402
from .distributors import (get_distributors_list, set_distributors_logger, set_distributors_progress, is_valid_api,
                           init_distributor_dict, configure_from_environment, configure_apis)
# KiCost definitions and modules/packages functions.
from .kicost import output_filename, kicost_gui_notdependences, kicost  # kicost core functions.
try:
    from .kicost_gui import kicost_gui
    GUI_ENABLED = True
except wxPythonNotPresent:
    # If the wxPython dependences are not installed and the user just want the KiCost CLI.
    GUI_ENABLED = False
from .spreadsheet import Spreadsheet
from .config import load_config, config_force_ttl, config_force_path
from . import __version__, __build__, debug_obsessive, debug_detailed, error, warning, info, get_logger, set_logger, KiCostError
from . import log


def init_all_loggers(main_logger, dist_logger, edas_logger):
    set_logger(main_logger)
    set_distributors_logger(dist_logger)
    set_edas_logger(edas_logger)


# Python 2.7 compatibility
try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError

###############################################################################
# Additional functions
###############################################################################


def kicost_version_info():
    build = __build__
    # Are we running from a repo? (including "pip install -e")
    prev_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if os.path.isdir(os.path.join(prev_dir, '.git')):
        cwd = os.getcwd()
        # Try to change to this place and find the git hash
        try:
            os.chdir(prev_dir)
            build = subprocess.check_output(['git', 'log', '-1', '--pretty=format:%h-%as']).decode('ascii')
        except (OSError, subprocess.CalledProcessError, FileNotFoundError):
            pass
        finally:
            os.chdir(cwd)
    version_info_str = r'KiCost v{} ({})'.format(__version__, build)
    version_info_str += r' at Python {}.{}.{}'.format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro)
    version_info_str += r' on {}({}). '.format(platform.platform(), platform.architecture()[0])
    try:
        import wx
        version_info_str += 'Graphical library: {}.'.format(wx.version())
    except ImportError:
        version_info_str += 'No graphical library installed for the GUI.'
    return version_info_str


class TqdmLoggingHandler(logging.Handler):
    '''Overload the class to write the logging through the `tqdm`.'''
    def __init__(self, stream, level=logging.NOTSET):
        super(self.__class__, self).__init__(level)
        self.stream = stream

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg, file=self.stream)  # , nolock=True)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)


class ProgressConsole(object):
    def __init__(self, total, logger):
        # Create a handler that emits using TQDM
        self.logTqdmHandler = TqdmLoggingHandler(sys.stderr)
        # Apply our custom formatter
        self.logTqdmHandler.setFormatter(log.CustomFormatter(sys.stderr))
        # Add as a handler and avoid propagating to the base class
        logger.addHandler(self.logTqdmHandler)
        logger.propagate = False
        self.logger = logger
        # Create the progress object
        self.progress = tqdm.tqdm(desc='Progress', total=total, unit='part', miniters=1, file=sys.stderr)

    def update(self, val):
        self.progress.update(val)

    def close(self):
        self.progress.close()
        self.logger.removeHandler(self.logTqdmHandler)
        self.logger.propagate = True


def command_line_api_options(api_options, args):
    """ Applies the command line options that overrides the APIs config """
    # Force API options from the command line
    if args.cache_ttl is not None:
        config_force_ttl(args.cache_ttl)
    if args.cache_path is not None:
        config_force_path(args.cache_path)
    if args.octopart_key is not None:
        api_options['Octopart']['key'] = args.octopart_key
    if args.octopart_level is not None:
        level = args.octopart_level
        extended = False
        if level[-1] == 'p':
            extended = True
            level = level[:-1]
        api_options['Octopart']['level'] = level
        api_options['Octopart']['extended'] = extended
    for api in args.disable_api:
        debug_obsessive('Disabling API ' + api)
        if is_valid_api(api):
            api_options[api]['enable'] = False
        else:
            warning(W_CMDLINE, 'Unknown API `{}`'.format(api))
    for api in args.enable_api:
        debug_obsessive('Enabling API ' + api)
        if is_valid_api(api):
            api_options[api]['enable'] = True
        else:
            warning(W_CMDLINE, 'Unknown API `{}`'.format(api))
    debug_detailed('Final API options {}'.format(api_options))


def configure_kicost_apis(config_file, overwrite, apply_user_opts, data):
    # Configuration file
    api_options = load_config(config_file)
    # Environment, overwrite only if the config file wasn't specified in the command line
    configure_from_environment(api_options, overwrite)
    # Apply command line options
    apply_user_opts(api_options, data)
    # Configure the APIs
    configure_apis(api_options)
    # Start with a clean list of available distributors
    init_distributor_dict()


###############################################################################
# Command-line interface.
###############################################################################


def main_real():

    parser = ap.ArgumentParser(
        description='Build cost spreadsheet for a KiCAD project.')
    parser.add_argument('-v', '--version',
                        action='version',
                        version='KiCost v{}'.format(__version__))
    parser.add_argument('--info',
                        action='version',
                        version=kicost_version_info(),
                        help='Show program\' and library information and version.')
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
    parser.add_argument('--translate_fields',
                        nargs='+',
                        type=str,
                        metavar='NAME',
                        help='''Specify or remove field translation
                            (--translate X1 Y1 X2 Y2 X3 ~,
                            translates X1 to Y1 and X2 to Y2 and remove
                            X3 for the internal dictionary).''')
    parser.add_argument('--variant',
                        nargs='+',
                        type=str,
                        default=[' '],  # Default variant is a space.
                        help='schematic variant name filter using regular expression.')
    parser.add_argument('-w', '--overwrite',
                        action='store_true',
                        help='Allow overwriting of an existing spreadsheet.')
    parser.add_argument('-q', '--quiet',
                        action='store_true',
                        help='Enable quiet mode with no warnings.')
    parser.add_argument('--ignore_fields',
                        nargs='+',
                        default=[],
                        help='Declare part fields to ignore when reading the BoM file.',
                        metavar='NAME',
                        type=str)
    parser.add_argument('--group_fields',
                        nargs='+',
                        default=[],
                        help='Declare part fields to merge when grouping parts.',
                        metavar='NAME',
                        type=str)
    parser.add_argument('--split_extra_fields',
                        nargs='+',
                        default=[],
                        help='Declare part fields to include in multipart split process.',
                        metavar='NAME',
                        type=str)
    parser.add_argument('--debug',
                        nargs='?',
                        type=int,
                        default=None,
                        metavar='LEVEL',
                        help='Print debugging info. (Larger LEVEL means more info.)')
    parser.add_argument('--eda', choices=get_registered_eda_names(),
                        nargs='+',
                        default=['kicad'],
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
    parser.add_argument('--show_cat_url',
                        action='store_true',
                        help='Do not suppress the catalogue links into the catalogue code in the spreadsheet.')
    parser.add_argument('-e', '--exclude',
                        nargs='+', type=str, default=[],
                        metavar='DIST',
                        help='Excludes the given distributor(s) from the scraping process.')
    parser.add_argument('--include',
                        nargs='+', type=str, default=[],
                        metavar='DIST',
                        help='Includes only the given distributor(s) in the scraping process.')
    parser.add_argument('--no_price',
                        action='store_true',
                        help='Create a spreadsheet without scraping part data from distributor websites.')
    parser.add_argument('--currency',
                        nargs='?',
                        type=str,
                        default='USD',
                        help='Define the priority currency. Use the ISO4217 for currency (`USD`, `EUR`). Default: `USD`.')
    parser.add_argument('-n', '--board_qty',
                        nargs='+', type=int, default=[Spreadsheet.DEFAULT_BUILD_QTY], metavar='QTY',
                        help='Number of boards to fabricate. Default: ' + str(Spreadsheet.DEFAULT_BUILD_QTY) + '.')
    parser.add_argument('--max_column_width',
                        nargs='?',
                        type=int,
                        default=DEF_MAX_COLUMN_W,
                        metavar='WIDTH',
                        help='Maximum column width. Using 0 disables the cell size adjust. Default: ' + str(DEF_MAX_COLUMN_W) + '.')
    parser.add_argument('--gui',
                        nargs='+',
                        type=str,
                        metavar='FILE.XML',
                        help='Start the GUI to run KiCost passing the file parameter give by "--input",'
                             ' all others parameters are ignored.')
    # SET: This is half imlemented. Not currently working.
    #     parser.add_argument('--user',
    #                         action='store_true',
    #                         help='Run KiCost on terminal using the parameters in the GUI memory, all passed parameters from'
    #                              ' terminal take priority.')
    parser.add_argument('--force_en_us',
                        action='store_true',
                        help='Workaround for broken wxWidgets locale on some Windows systems.')
    parser.add_argument('--setup',
                        action='store_true',
                        help='Run KiCost integration (with KiCad and OS) configuration script.')
    parser.add_argument('--unsetup',
                        action='store_true',
                        help='Undo the KiCost integration.')
    parser.add_argument('--octopart_key',
                        nargs='?', type=str, metavar='APIKEY',
                        help='Enable Octopart using the provided key. Use None to disable it.')
    parser.add_argument('--octopart_level',
                        nargs='?', type=str, metavar='APILEVEL', choices=['3', '3p', '4', '4p'],
                        help='Use Octopart API level. Can be 3 or 4 for basic API and 3p or 4p for PRO plans. Default: 4')
    parser.add_argument('--disable_api',
                        nargs='+', type=str, default=[],
                        metavar='API',
                        help='Disable the listed APIs.')
    parser.add_argument('--enable_api',
                        nargs='+', type=str, default=[],
                        metavar='API',
                        help='Enable the listed APIs.')
    parser.add_argument('-c', '--config',
                        nargs='?', type=str,
                        metavar='CONFIG.YAML',
                        help='Configuration file.')
    parser.add_argument('--cache_ttl',
                        nargs='?', type=float,
                        metavar='DAYS',
                        help='Force the Time To Live for the APIs caches.')
    parser.add_argument('--cache_path',
                        nargs='?', type=str,
                        metavar='BASE_PATH',
                        help='Force the base path for the APIs caches.')

    args = parser.parse_args()

    # Set up logging verbosity
    log.set_domain('kicost')
    init_all_loggers(log.init(), log.get_logger('kicost.distributors'), log.get_logger('kicost.edas'))
    log.set_verbosity(get_logger(), args.debug, args.quiet)
    set_distributors_progress(ProgressConsole)

    # Now we can print errors, inform if YAML is missing
    try:
        import yaml  # noqa F401
    except ImportError:
        error('No yaml module for Python, install it (i.e. python3-yaml)')

    # APIs Configuration
    configure_kicost_apis(args.config, args.config is None, command_line_api_options, args)

    # Setup and unsetup KiCost integration.
    if args.setup:
        from .kicost_config import kicost_setup
        kicost_setup()
        return
    if args.unsetup:
        from .kicost_config import kicost_unsetup
        kicost_unsetup()
        return

    # Simple commands
    if args.show_dist_list:
        info('Distributor list: ' + ' '.join(sorted(get_distributors_list())))
        sys.exit(0)
    if args.show_eda_list:
        info('EDA supported list: ' + ' '.join(sorted(get_registered_eda_names())))
        sys.exit(0)

    # Set up spreadsheet output file.
    if args.output is None:
        # If no output file is given...
        if args.input is not None:
            # Send output to spreadsheet with name of input file.
            # Compose a name with the multiple BOM input file names.
            args.output = output_filename(args.input)
        else:
            # Send output to spreadsheet with name of this application.
            args.output = os.path.splitext(sys.argv[0])[0] + '.xlsx'
    else:
        # Output file was given. Make sure it has spreadsheet extension.
        args.output = os.path.splitext(args.output)[0] + '.xlsx'

    # SET: This is half implemented. Not currently working.
    #     # Call the KiCost interface to alredy run KiCost, this is just to use the
    #     # saved user configurations of the graphical interface.
    #     if args.user:
    #         if not GUI_ENABLED:
    #             kicost_gui_notdependences()
    #         kicost_gui_runterminal(args)
    #         sys.exit(0)

    # Handle case where output is going into an existing spreadsheet file.
    if os.path.isfile(args.output):
        if not args.overwrite:
            error('Output file {} already exists!\nUse the --overwrite option to replace it.'.format(args.output))
            sys.exit(2)

    if args.gui:
        if not GUI_ENABLED:
            kicost_gui_notdependences()
        kicost_gui(args.force_en_us, [os.path.abspath(fileName) for fileName in args.gui])
        sys.exit(0)

    if args.input is None:
        if not GUI_ENABLED:
            kicost_gui_notdependences()
        kicost_gui(args.force_en_us)  # Use the user gui if no input is given.
        sys.exit(0)
    else:
        # Match the EDA tool formats with the input files.
        if len(args.eda) == 1:
            # Expand a single EDA format to cover all input files.
            args.eda = args.eda[0:1] * len(args.input)
        if len(args.input) != len(args.eda):
            error('The number of input files must match the number of EDA tool formats.')
            sys.exit(2)

        # Match the variants with the input files.
        if len(args.variant) == 1:
            args.variant = args.variant[0:1] * len(args.input)
        if len(args.input) != len(args.variant):
            error('The number of input files must match the number of variants.')
            sys.exit(2)

        # Match the board quantities with the input files.
        if len(args.board_qty) == 1:
            args.board_qty = args.board_qty[0:1] * len(args.input)
        if len(args.input) != len(args.board_qty):
            error('The number of input files must match the number of board quantities.')
            sys.exit(2)

        # Otherwise get XML from the given file.
        for i in range(len(args.input)):
            # Set '.xml' as the default file extension, treating this exception
            # allow other files extension and formats.
            try:
                if os.path.splitext(args.input[i])[1] == '':
                    args.input[i] += '.xml'
                elif os.path.splitext(args.input[i])[1] == '.csv':
                    args.eda[i] = 'csv'
            except IndexError:
                pass

    # List of distributors to scrape
    available = get_distributors_list()
    for d in args.include + args.exclude:
        if d not in available:
            error('Unknown distributor requested: `{}`'.format(d))
            sys.exit(2)
    if args.no_price:
        # None
        dist_list = []
    else:
        if not args.include:
            # All by default
            dist_list = available
        else:
            # Requested to be included
            dist_list = args.include
        # Requested to be excluded
        for d in args.exclude:
            dist_list.remove(d)

    debug_obsessive('Started ' + kicost_version_info())

    kicost(in_file=args.input, eda_name=args.eda,
           out_filename=args.output, collapse_refs=not args.no_collapse, suppress_cat_url=not args.show_cat_url,
           user_fields=args.fields, ignore_fields=args.ignore_fields,
           group_fields=args.group_fields, translate_fields=args.translate_fields,
           variant=args.variant, dist_list=dist_list, currency=args.currency, max_column_width=args.max_column_width,
           split_extra_fields=args.split_extra_fields, board_qty=args.board_qty)


def main():
    try:
        main_real()
    except KiCostError as e:
        error(e.msg)
        sys.exit(e.id)


###############################################################################
# Main entrypoint.
###############################################################################
if __name__ == '__main__':
    start_time = time.time()
    main()
    debug_obsessive('Elapsed time: %f seconds', time.time() - start_time)
