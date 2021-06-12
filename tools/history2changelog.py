#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) 2021 Salvador E. Tropea
# Copyright (c) 2021 Instituto Nacional de Tecnología Industrial
# License: MIT
# Project: KiCost
"""
Tool to convert the HISTORY.rst into a CHANGELOG.md
"""
import sys
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
    for l in fin:
        if l[0].isnumeric():
            if started:
                gen(added, 'Added')
                gen(changed, 'Changed')
                gen(fixed, 'Fixed')
            m = re.match(r'(.*) \((.*)\)', l)
            print('## [' + m.group(1) + '] - ' + m.group(2))
            started = True
            added = []
            fixed = []
            changed = []
        elif l[0] != '_':
            l = l.strip()
            if l and started:
                if l.startswith('* Fixed'):
                    fixed.append(l[8:])
                elif l.startswith('* Fix'):
                    fixed.append(l[6:])
                elif l.startswith('* Added'):
                    added.append(l[8:])
                elif l.startswith('* Add'):
                    added.append(l[6:])
                elif l.startswith('* Changed'):
                    changed.append(l[10:])
                else:
                    changed.append(l[2:])
                started = True
gen(added, 'Added')
gen(changed, 'Changed')
gen(fixed, 'Fixed')

