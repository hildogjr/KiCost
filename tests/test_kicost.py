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


def run_test(inputs, output, extra=None):
    cmd = ['kicost', '--no_price']
    if extra:
        cmd.extend(extra)
    out_xlsx = 'tests/' + output + '.xlsx'
    cmd.extend(['-o', out_xlsx])
    cmd.extend(['-wi'] + ['tests/' + n for n in inputs])
    logging.debug('Running '+str(cmd))
    subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    res_csv = 'tests/result_test/' + output + '.csv'
    logging.debug('Converting to CSV')
    p1 = subprocess.Popen(['xlsx2csv', '--skipemptycolumns', out_xlsx], stdout=subprocess.PIPE)
    with open(res_csv, 'w') as f:
        p2 = subprocess.Popen(['egrep', '-i', '-v', r'(\$ date|kicost|Total purchase)'], stdin=p1.stdout, stdout=f)
        p2.communicate()[0]
    ref_csv = 'tests/expected_test/' + output + '.csv'
    cmd = ['diff', '-u', ref_csv, res_csv]
    logging.debug('Running '+str(cmd))
    subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    logging.info(output+' OK')


def test_multiproject_1():
    test_name = 'multiproject_1'
    try:
        run_test(['multipart', 'multipart2.xml'], 'multipart1+2')
    except subprocess.CalledProcessError as e:
        logging.error('Failed test: '+test_name)
        if e.output:
            logging.error('Output from command: ' + e.output.decode())
        raise e


def test_variants_1():
    test_name = 'variants_1'
    try:
        run_test(['variants_1'], 'variants_1_test', ['--variant', 'test'])
        run_test(['variants_1'], 'variants_1_production', ['--variant', 'production'])
        run_test(['variants_1'], 'variants_1_default', ['--variant', 'default'])
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
