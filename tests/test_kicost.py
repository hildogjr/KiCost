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
                subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                logging.info(f + ' OK')
            except subprocess.CalledProcessError as e:
                logging.error('Failed test: '+f)
                if e.output:
                    logging.error('Output from command: ' + e.output.decode())
                # logfile = os.path.join('log_test', f + '.log')
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


def test_multiproject_1():
    test_name = 'multiproject_1'
    try:
        cmd = ['kicost', '--no_price',
               '-o', 'tests/multipart1+2.xlsx',
               '-wi', 'tests/multipart.xml', 'tests/multipart2.xml']
        logging.debug('Running '+str(cmd))
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        cmd = ['xlsx2csv', 'tests/multipart1+2.xlsx', 'tests/result_test/multipart1+2.csv.tmp']
        logging.debug('Running '+str(cmd))
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        cmd = ['egrep', '-i', '-v', r'(\$ date|kicost|Total purchase)', 'tests/result_test/multipart1+2.csv.tmp']
        with open('tests/result_test/multipart1+2.csv', 'w') as f:
            logging.debug('Running '+str(cmd))
            subprocess.call(cmd, stdout=f)
        cmd = ['diff', '-u', 'tests/expected_test/multipart1+2.csv', 'tests/result_test/multipart1+2.csv']
        logging.debug('Running '+str(cmd))
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        logging.info(test_name+' OK')
    except subprocess.CalledProcessError as e:
        logging.error('Failed test: '+test_name)
        if e.output:
            logging.error('Output from command: ' + e.output.decode())
        raise e


class TestKicost(unittest.TestCase):

    def setUp(self):
        pass

    def test_something(self):
        pass

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
