#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) 2021 Salvador E. Tropea
# Copyright (c) 2021 Instituto Nacional de Tecnología Industrial
# License: MIT
# Project: KiCost
"""
Tool to convert the HISTORY.rst into a CHANGELOG.md
"""
import re
import os.path as op


def gen(lst, name):
    if lst:
        print('### ' + name)
        for a in lst:
            a = a.replace('``', '`')
            print('- ' + a[0].upper() + a[1:])
        print()


history_filename = op.join(op.dirname(op.abspath(op.dirname(__file__))), 'kicost', 'HISTORY.rst')

print('''# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
''')

started = False
with open(history_filename, "rt") as fin:
    for ln in fin:
        if ln[0].isnumeric():
            if started:
                gen(added, 'Added')      # noqa: F821
                gen(changed, 'Changed')  # noqa: F821
                gen(fixed, 'Fixed')      # noqa: F821
            m = re.match(r'(.*) \((.*)\)', ln)
            print('## [' + m.group(1) + '] - ' + m.group(2))
            started = True
            added = []
            fixed = []
            changed = []
        elif ln[0] != '_':
            ln = ln.strip()
            if ln and started:
                if ln.startswith('* Fixed'):
                    fixed.append(ln[8:])
                elif ln.startswith('* Fix'):
                    fixed.append(ln[6:])
                elif ln.startswith('* Added'):
                    added.append(ln[8:])
                elif ln.startswith('* Add'):
                    added.append(ln[6:])
                elif ln.startswith('* Changed'):
                    changed.append(ln[10:])
                else:
                    changed.append(ln[2:])
                started = True
gen(added, 'Added')
gen(changed, 'Changed')
gen(fixed, 'Fixed')
