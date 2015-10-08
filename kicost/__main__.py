# MIT license
# 
# Copyright (C) 2015 by XESS Corporation
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
from __future__ import absolute_import

import argparse as ap
import os
import sys
from .__init__ import __version__
from .kicost import *

def main():
    parser = ap.ArgumentParser(
        description='Build cost spreadsheet for a KiCAD project.')
    parser.add_argument('-v', '--version',
                        action='version',
                        version='KiCost ' + __version__)
    parser.add_argument('-i', '--input',
                        nargs='?',
                        type=str,
                        metavar='file.xml',
                        help='Schematic BOM XML file.')
    parser.add_argument('-o', '--output',
                        nargs='?',
                        type=str,
                        metavar='file.xlsx',
                        help='Generated cost spreadsheet.')
    parser.add_argument('-w', '--overwrite',
                        action='store_true',
                        help='Allow overwriting of an existing spreadsheet.')
    parser.add_argument(
        '-d', '--debug',
        nargs='?',
        type=int,
        default=0,
        metavar='LEVEL',
        help='Print debugging info. (Larger LEVEL means more info.)')

    args = parser.parse_args()

    if args.output == None:
        if args.input != None:
            args.output = os.path.splitext(args.input)[0] + '.xlsx'
        else:
            args.output = os.path.splitext(sys.argv[0])[0] + '.xlsx'
    else:
        args.output = os.path.splitext(args.output)[0] + '.xlsx'
    if os.path.isfile(args.output):
        if not args.overwrite:
            print('Output file {} already exists! Use the --overwrite option to replace it.'.format(
                args.output))
            sys.exit(1)

    if args.input == None:
        args.input = sys.stdin
    else:
        args.input = os.path.splitext(args.input)[0] + '.xml'
        args.input = open(args.input)

    kicost(in_file=args.input, out_filename=args.output, debug_level=args.debug)

# main entrypoint.
if __name__ == '__main__':
    main()