#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_kicost
----------------------------------

Tests for `kicost` module.
"""

import unittest
import subprocess
import logging
import glob
import os

from kicost import kicost


def do_test_single(pattern):
    os.chdir('tests')
    fail = False
    if not os.path.isdir('result_test'):
        os.mkdir('result_test')
    if not os.path.isdir('log_test'):
        os.mkdir('log_test')
    try:
        for f in glob.glob(pattern):
            try:
                cmd = ['./test_single.sh', '--no_price', f]
                logging.debug('Running '+str(cmd))
                res = subprocess.check_output(['./test_single.sh', '--no_price', f], stderr=subprocess.STDOUT)
                logging.info(f + ' OK')
            except subprocess.CalledProcessError as e:
                logging.error('Failed test: '+f)
                if e.output:
                    logging.error('Output from command: ' + e.output.decode())
                logfile = os.path.join('log_test', f + '.log')
                # if os.path.isfile(logfile):
                #     with open(logfile, 'rt') as f:
                #         msg = f.read()
                #     logging.error('Logfile: ' + msg)
                fail = True
                pass
    finally:
        os.chdir('..')
    return fail


def test_xmls():
    assert not do_test_single('*.xml')


def test_csvs():
    assert not do_test_single('*.csv')


class TestKicost(unittest.TestCase):

    def setUp(self):
        pass

    def test_something(self):
        pass

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
