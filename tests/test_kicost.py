#!/usr/bin/env python
# -*- coding: utf-8 -*-

# MIT license
#
# Copyright (c) 2021 Salvador E. Tropea
# Copyright (c) 2021 Instituto Nacional de Tecnologïa Industrial
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

"""
KiCost test module

Tests for `kicost`. From the root of the projectr run:

pytest-3 --log-cli-level debug
"""

import unittest
import subprocess
import logging
import os
import re
import sys
import shutil
import xml.etree.ElementTree as ET
from kicost.global_vars import ERR_FIELDS

# Author information.
__author__ = 'Salvador Eduardo Tropea'
__webpage__ = 'https://github.com/set-soft/'
__company__ = 'INTI-CMNB - Argentina'

# Collect real world queries (see README.md)
# Change to 1 when the query result must be saved, then revert to 0
ADD_QUERY_TO_KNOWN = 0
# Used to regenerate the references
CREATE_REF = 0
TESTDIR = os.path.dirname(os.path.realpath(__file__))
last_err = None
# Text we want to filter in the XLSX to TXT conversion
XLSX_FILTERS = (('$ date:', None), ('Prj date:', '(file'), ('KiCost', 0))
OCTOPART_KEY = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'


def to_str(s):
    if s is None or sys.version_info[0] >= 3:
        return s
    return s.encode('utf-8')


def log_running(what, cmd):
    logging.debug('{} using: {}'.format(what, ' '.join(cmd)))


def xlsx_to_txt(filename, subdir='result_test', sheet=1):
    filename = os.path.join(TESTDIR, filename + '.xlsx')
    logging.debug('Converting to TXT')
    tmpdir = TESTDIR + '/desc'
    assert not os.path.isdir(tmpdir), "Destination for XLSX uncompress is there, remove it and investigate"
    subprocess.call(['unzip', filename, '-d', tmpdir])
    # Some XMLs are stored with 0600
    subprocess.call(['chmod', '-R', 'og+r', tmpdir])
    # Read the table
    worksheet = os.path.join(tmpdir, 'xl', 'worksheets', 'sheet'+str(sheet)+'.xml')
    if not os.path.isfile(worksheet):
        return False
    rows = []
    forms = {}
    root = ET.parse(worksheet).getroot()
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    for r in root.iter(ns+'row'):
        rcur = int(r.attrib['r'])
        cols = []
        for cell in r.iter(ns+'c'):
            if 't' in cell.attrib:
                type = cell.attrib['t']
            else:
                type = 'n'   # default: number
            pos = cell.attrib['r']
            value = cell.find(ns+'v')
            if value is not None:
                if type == 'n':
                    # Numbers as integers
                    value = float(value.text) if value.text is not None else None
                else:
                    value = value.text
            cols.append((pos, value))
            form = cell.find(ns+'f')
            if form is not None:
                text = str(form.text)
                forms[pos] = text.replace('\n', r'\n')
        rows.append((rcur, cols))
    # Conditional formatting
    # Styles first
    styles = os.path.join(tmpdir, 'xl', 'styles.xml')
    dxfs = []
    for d in ET.parse(styles).getroot().find(ns+'dxfs').iter(ns+'dxf'):
        fg = '-'
        font = d.find(ns+'font')
        if font:
            fg = font.find(ns+'color').attrib['rgb']
        bg = '-'
        fill = d.find(ns+'fill')
        if fill:
            fill = fill.find(ns+'patternFill')
            if fill:
                bg = fill.find(ns+'bgColor').attrib['rgb']
        dxfs.append(fg+'/'+bg)
    # Now the conditions
    cond_f = {}
    for c in root.iter(ns+'conditionalFormatting'):
        pos = c.attrib['sqref']
        conds = []
        for rule in c.iter(ns+'cfRule'):
            form = rule.find(ns+'formula')
            type = rule.attrib['type']
            if type == 'cellIs':
                txt = rule.attrib['operator'] + ' ' + form.text
            else:
                txt = '=' + form.text
            conds.append((txt, dxfs[int(rule.attrib['dxfId'])], int(rule.attrib['priority'])))
        cond_f[pos] = conds
    # Links are "Relationship"s
    links = {}
    urls = {}
    nr = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
    hlinks = root.find(ns+'hyperlinks')
    if hlinks:
        for r in hlinks.iter(ns+'hyperlink'):
            links[r.attrib['ref']] = r.attrib[nr+'id']
    # Read the strings
    strings = os.path.join(tmpdir, 'xl', 'sharedStrings.xml')
    # The cast to str is to support obsolete Python versions
    strs = [to_str(t.text) for t in ET.parse(strings).getroot().iter(ns+'t')]
    # Translate the links
    if links:
        # Read the relationships
        worksheet = os.path.join(tmpdir, 'xl', 'worksheets', '_rels', 'sheet'+str(sheet)+'.xml.rels')
        root = ET.parse(worksheet).getroot()
        rels = {}
        for r in root:
            rels[r.attrib['Id']] = r.attrib['Target']
        for pos, id in links.items():
            urls[pos] = rels[id]
    # Get the global definitions
    workbook = os.path.join(tmpdir, 'xl', 'workbook.xml')
    dnames = ET.parse(workbook).getroot().find(ns+'definedNames')
    vars = {}
    for dname in dnames.iter(ns+'definedName'):
        name = dname.attrib['name']
        vars[name] = dname.text
    name = os.path.basename(filename)
    pos_re = re.compile(r'(\D+)(\d+)')
    with open(os.path.join(TESTDIR, subdir, name + '.txt'), 'wt') as f:
        f.write('Variables:\n')
        for name, val in sorted(vars.items()):
            f.write(name + ' = ' + val + '\n')
        f.write('-'*80+'\n')
        used_cells = set()
        for r in rows:
            f.write('Row: ' + str(r[0]) + '\n')
            skip_next_col = False
            skip_str = None
            for col in r[1]:
                pos = col[0]
                used_cells.add(pos)
                m = pos_re.match(pos)
                cell = col[1]
                form = forms.get(pos)
                styles = cond_f.get(pos)
                if cell is None and form is None and styles is None:
                    continue
                f.write(' Col: ' + m.group(1) + '\n')
                if cell is not None:
                    f.write('   ')
                if isinstance(cell, str):
                    try:
                        text = '*NONE*' if cell == 'None' else strs[int(cell)]
                    except ValueError:
                        # Special cases where the text is there
                        text = cell
                    if text is None:
                        text = '*NONE*'
                    # Filter variable fields
                    if skip_next_col and (skip_str is None or skip_str in text):
                        f.write('*FILTERED*\n')
                        skip_next_col = False
                        continue
                    for filter in XLSX_FILTERS:
                        if text.startswith(filter[0]):
                            if filter[1] == 0:
                                text = '*FILTERED*'
                                break
                            skip_next_col = True
                            skip_str = filter[1]
                    url = urls.get(pos)
                    if url:
                        f.write('<a href="{}">{}</a>'.format(url, text))
                    else:
                        f.write('"' + text + '"')
                elif cell is not None:
                    # Python 2.7 str(float) has only 12 digits
                    # Forcing 16 fails in some cases
                    f.write("{:.12g}".format(cell))
                if cell is not None:
                    f.write('\n')
                if form:
                    f.write('  Formula: ' + form + '\n')
                if styles:
                    f.write('  Styles:\n')
                    for style in styles:
                        # f.write('  - {} -> {} ({})\n'.format(style[0], style[1], style[2]))
                        # The priority doesn't look really important and generates a lot of silly diffs
                        f.write('  - {} -> {}\n'.format(style[0], style[1]))
        # Orphan conditional formatting
        for pos in sorted(cond_f.keys()):
            if pos not in used_cells:
                f.write('Cell: ' + pos + '\n')
                for style in cond_f[pos]:
                    f.write(' - {} -> {}\n'.format(style[0], style[1]))
    shutil.rmtree(tmpdir)
    return True


def xlsx_to_csv(filename, subdir='result_test', price=True):
    res_csv = os.path.join(TESTDIR, subdir, filename + '.csv')
    out_xlsx = os.path.join(TESTDIR, filename + '.xlsx')
    # Convert to CSV
    logging.debug('Converting to CSV')
    cmd = ['xlsx2csv']
    if not price:
        cmd.append('--skipemptycolumns')
    cmd.append(out_xlsx)
    p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    # Filter it
    filter = r'\$ date|Prj date:.*\(file|kicost'
    if not price:
        filter += '|Total purchase'
    with open(res_csv, 'w') as f:
        p2 = subprocess.Popen(['egrep', '-i', '-v', '(' + filter + ')'], stdin=p1.stdout, stdout=f)
        p2.communicate()[0]


def check_diff(filename):
    ref = os.path.join(TESTDIR, 'expected_test', filename)
    res = os.path.join(TESTDIR, 'result_test', filename)
    cmd = ['diff', '-u', ref, res]
    log_running('Comparing', cmd)
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        logging.error(e.output.decode('utf-8'))
        raise


def run_test(name, inputs, output, extra=None, price=True, ret_err=0, config_file=None):
    if not os.path.isdir(TESTDIR + '/result_test'):
        os.mkdir(TESTDIR + '/result_test')
    if not os.path.isdir(TESTDIR + '/log_test'):
        os.mkdir(TESTDIR + '/log_test')
    # Always fake the currency rates
    os.environ['KICOST_CURRENCY_RATES'] = TESTDIR + '/currency_rates.xml'
    # Now choose between recording the KitSpace queries or fake them
    if price and ADD_QUERY_TO_KNOWN:
        os.environ['KICOST_LOG_HTTP'] = TESTDIR + '/kitspace_queries.txt'
        with open(TESTDIR + '/kitspace_queries.txt', 'at') as f:
            if len(inputs) == 1:
                f.write('# ' + inputs[0] + '\n')
            else:
                f.write('# ' + str(inputs) + '\n')
        server = None
    else:
        os.environ['KICOST_KITSPACE_URL'] = 'http://localhost:8000'
        os.environ['KICOST_OCTOPART_URL'] = 'http://localhost:8000'
        fo = open(TESTDIR + '/log_test/0server_stdout.log', 'at')
        fe = open(TESTDIR + '/log_test/0server_stderr.log', 'at')
        server = subprocess.Popen(TESTDIR + '/dummy-web-server.py', stdout=fo, stderr=fe)
    # Run KiCost
    cmd = ['src/kicost', '--debug', '10']
    if not price:
        cmd.append('--no_price')
    if extra:
        cmd.extend(extra)
    if config_file is not None:
        cmd.extend(['-c', TESTDIR + '/configs/' + config_file])
    else:
        cmd.extend(['-c', TESTDIR + '/configs/default.yaml'])
    out_xlsx = TESTDIR + '/' + output + '.xlsx'
    cmd.extend(['-o', out_xlsx])
    cmd.extend(['-wi'] + [TESTDIR + '/' + n for n in inputs])
    log_running('Testing', cmd)
    log_err = open(TESTDIR + '/log_test/' + output + '_error.log', 'w+t')
    log_out = open(TESTDIR + '/log_test/' + output + '_out.log', 'w+t')
    ret = subprocess.call(cmd, stderr=log_err, stdout=log_out)
    # Kill the server
    if server is not None:
        server.terminate()
        fo.close()
        fe.close()
    global last_err
    log_err.seek(0)
    last_err = log_err.read()
    log_err.close()
    log_out.close()
    # Check return value
    if ret_err != ret:
        logging.error('Failed test: ' + name)
        assert False, last_err
    # Convert to CSV/TXT
    if not ret_err:
        if CREATE_REF:
            xlsx_to_csv(output, 'expected_test', price)
            xlsx_to_txt(output, 'expected_test')
        else:
            xlsx_to_csv(output, 'result_test', price)
            check_diff(output + '.csv')
            xlsx_to_txt(output, 'result_test')
            check_diff(output + '.xlsx.txt')
    logging.info(output+' OK')


def run_test_check(name, inputs=None, output=None, extra=None, price=True, ret_err=0, config_file=None):
    logging.debug('Test name: ' + name)
    if inputs is None:
        inputs = name
    if isinstance(inputs, str):
        inputs = [inputs]
    if output is None:
        output = inputs[0]
        if output.endswith('.csv'):
            output = output[:-4]
    run_test(name, inputs, output, extra, price, ret_err, config_file)


def check_errors(errors):
    res = []
    global last_err
    for error in errors:
        m = re.search(error, last_err, re.MULTILINE)
        assert m is not None, error
        logging.debug('error match: `{}` (`{}`) OK'.format(error, m.group(0)))
        res.append(m)
    return res


def test_300_010():
    run_test_check('300-010')


def test_acquire_PWM_1():
    run_test_check('acquire-PWM', config_file='kitspace_no_cache.yaml')


def test_acquire_PWM_dk():
    name = 'acquire_PWM_dk'
    run_test_check(name, 'acquire-PWM', name, extra=['--include', 'digikey'], config_file='digikey.yaml')


def test_acquire_PWM_eur_dk():
    name = 'acquire_PWM_eur_dk'
    run_test_check(name, 'acquire-PWM', name, extra=['--include', 'digikey', '--currency', 'EUR'], config_file='digikey_eur.yaml')


def test_acquire_PWM_2():
    run_test_check('acquire-PWM_2', config_file='kitspace_no_cache.yaml')


def test_Aeronav_R():
    run_test_check('Aeronav_R')


def test_b3u():
    run_test_check('b3u_test')


def test_bbsram():
    run_test_check('bbsram')


def test_BoulderCreekMotherBoard():
    # This test doesn't have any kind of manf# or DISTRIBUTOR#
    run_test_check('BoulderCreekMotherBoard', price=False)


def test_CAN_Balancer():
    run_test_check('CAN Balancer')


def test_Decoder():
    run_test_check('Decoder')


def test_fitting():
    run_test_check('fitting_test')


def test_Indium_X2():
    run_test_check('Indium_X2')


def test_kc():
    run_test_check('kc-test')


def test_LedTest():
    run_test_check('LedTest')


def test_local_Indium_X2():
    run_test_check('local_Indium_X2')


def test_NF6X_TestBoard():
    run_test_check('NF6X_TestBoard')


def test_Receiver_1W():
    run_test_check('Receiver_1W')


def test_RPi():
    run_test_check('RPi-Test')


def test_RX_LR_lite():
    run_test_check('RX LR lite')


def test_safelink_receiver():
    run_test_check('safelink_receiver')


def test_single_component():
    run_test_check('single_component')


def test_StickIt_Hat_old():
    run_test_check('StickIt-Hat-old')


def test_StickIt_Hat_new():
    run_test_check('StickIt-Hat')


def test_StickIt_QuadDAC():
    run_test_check('StickIt-QuadDAC')


def test_StickIt_RotaryEncoder():
    # Tests an embedded price from Aliexpress
    run_test_check('StickIt-RotaryEncoder')


def test_subparts():
    run_test_check('subparts')


def test_subparts_err1():
    # Here we ask to repeat the manufacturer, but in the first position, nothing to repeat
    run_test_check('subparts_err1')


def test_1():
    run_test_check('test')


def test_2a():
    run_test_check('test2')


def test_2e():
    name = 'test_2e'
    run_test_check(name, 'test2', name, extra=['--currency', 'EUR'])


def test_3_():
    run_test_check('test3')


def test_Parts():
    run_test_check('TestParts')


def test_part_list_big():
    run_test_check('part_list_big.csv', config_file='kitspace_no_cache.yaml')


def test_part_list_small_hdr():
    run_test_check('part_list_small.csv', config_file='kitspace_no_cache.yaml')


def test_part_list_small_nohdr():
    run_test_check('part_list_small_nohdr.csv', config_file='kitspace_no_cache.yaml')


def test_multiproject_1():
    run_test_check('multiproject_1 (1 single)', 'multipart')
    run_test_check('multiproject_1 (2 single)', 'multipart2')
    run_test_check('multiproject_1', ['multipart', 'multipart2.xml'], 'multipart1+2')


def test_board_qty_1():
    # Check we can select 50 boards
    run_test_check('test_board_qty_1', 'test', 'board_qty_1', ['--board_qty', '50'])


def test_board_qty_2():
    # Check we can select 50 and 70 boards
    run_test_check('test_board_qty_2', ['multipart', 'multipart2.xml'], 'board_qty_2', ['--board_qty', '50', '70'])


def test_board_qty_3():
    # Check we can select 30 for all
    run_test_check('test_board_qty_3', ['multipart', 'multipart2.xml'], 'board_qty_3', ['--board_qty', '30'])


def test_variants_1():
    # This test doesn't have any kind of manf# or DISTRIBUTOR#
    test_name = 'variants_1'
    run_test_check(test_name, 'variants_1', price=False)
    run_test_check(test_name + '(test)', 'variants_1', 'variants_1_test', ['--variant', 'test'], price=False)
    run_test_check(test_name + '(production)', 'variants_1', 'variants_1_production', ['--variant', 'production'], price=False)
    run_test_check(test_name + '(default)', 'variants_1', 'variants_1_default', ['--variant', 'default'], price=False)


def test_variants_2():
    # This test is related to issue #474
    # Tests the same as test_manf_no_manf_num() but in a variant case
    # Note that we don't even have manf#, no price here
    test_name = 'variants_2'
    run_test_check(test_name, 'variants_2', price=False)
    run_test_check(test_name + '(variant1)', 'variants_2', 'variants_2_variant1', ['--variant', 'variant1'], price=False)


def test_variants_3():
    # This test doesn't have any kind of manf# or DISTRIBUTOR#
    # Tests some variant overwrites
    test_name = 'variants_3'
    run_test_check(test_name, 'variants_3', price=False)
    # Run a test with parameter "variant1"
    run_test_check(test_name + '(variant1)', 'variants_3', 'variants_3_variant1', ['--variant', '^(variant1)$', '--fields', 'Comment'], price=False)


def test_user_fields_1():
    run_test_check('user_fields_1', '300-010', 'user_fields_1', extra=['--fields', "Resistance", "Capacitance", "Voltage", "Tolerance"])


def test_complex_multipart():
    # This testcase has to be updated once multipart custom pricing has been better defined
    test_name = 'complex_multipart'
    fields = ['S1MN', 'S1PN', 'S2MN', 'S2PN']
    run_test_check(test_name, 'complex_multipart', extra=['--split_extra_fields'] + fields + ['-f'] + fields, price=True)


def test_include_1():
    # Explicitly request digikey and mouser
    run_test_check('include_1', 'fitting_test', 'include_1', extra=['--include', 'digikey', 'mouser'])


def test_exclude_1():
    # Implicitly request digikey and mouser
    run_test_check('exclude_1', 'fitting_test', 'exclude_1', extra=['--exclude', 'arrow', 'farnell', 'lcsc', 'newark', 'rs', 'tme'])


def test_scrape_over_1():
    # Data from the fields is added to the web-scraped data
    run_test_check('scrape_over')


def test_scrape_over_2():
    # Data from the fields relaces the web-scraped data.
    # For this we exclude the distributor with --exclude
    run_test_check('scrape_over_2', 'scrape_over', 'scrape_over_2', extra=['--exclude', 'rs'], config_file='kitspace_no_cache.yaml')


def test_manf_no_manf_num():
    # Two similar parts, but from different manufacturer and no manf#
    # Issue #474
    run_test_check('manf_no_manf_num')


def test_parts_and_comments():
    # Similar to test_no_empty_overwrite, tests all possible manf# aliases
    run_test_check('parts_and_comments', extra=['--group_fields', 'h', 'comment',
                   '--no_collapse', '-f', 'comment', 'S1MN', 'S1PN', 'S2MN', 'S2PN'], price=False)


def test_group_1():
    # Similar to test_no_empty_overwrite, tests all possible manf# aliases
    run_test_check('group_1_group_fields', 'group_1', output='group_1_group_fields',
                   extra=['--group_fields', 'h', 'comment', '--no_collapse', '-f', 'comment', 'S1MN', 'S1PN', 'S2MN', 'S2PN'],
                   price=False)
    run_test_check('group_1_ignore_comment', 'group_1', output='group_1_ignore_comment',
                   extra=['--ignore_fields', 'h', 'comment', '--no_collapse', '-f', 'comment', 'S1MN', 'S1PN', 'S2MN', 'S2PN'],
                   price=False)


def test_423():
    # Test for issue #423
    # This test checks that we interpret a numeric manf# code as a string
    # The "OK" tests uses the real manf#
    # The "Wrong" tests uses an invalid value, reported in #423
    # Checking how it looks in the spreadsheet software needs manual inspect, but currently we use "write_string".
    # Any "scientic notation" is a bug in the spreadsheet software. MS Excel does it right.
    run_test_check('Test 423 CSV Ok', 'test_423_ok.csv', 'test_423_csv_ok')
    run_test_check('Test 423 CSV Wrong', 'test_423_wrong.csv', 'test_423_csv_wrong')
    run_test_check('Test 423 XML Ok', 'test_423_ok', 'test_423_xml_ok')
    run_test_check('Test 423 XML Wrong', 'test_423_wrong', 'test_423_xml_wrong')


def disabled_test_sub_part_group_propagate_266():
    # Test Issue #266
    #  SubPart manf# field should also propagate
    run_test_check('SubPartGroupTest_266', price=False)


def test_no_empty_overwrite():
    # Test some cases where we overwrite a field using an alias (i.e. mnp changes manf#)
    # See discusion on #471
    run_test_check('no_empty_overwrite', price=False)


def test_wrong_pricing():
    # File with errors in the pricing field
    run_test_check('wrong_pricing', extra=['--include', 'arrow', '--exclude', 'arrow'])
    check_errors([r'Malformed pricing number(.*)STK1', r'Malformed pricing entry(.*)PCB1'])


def test_wrong_currency():
    # File with a wrong currency
    run_test_check('wrong_currency', extra=['--include', 'arrow', '--exclude', 'arrow'], ret_err=ERR_FIELDS)
    check_errors([r'XXX is not a supported currency in STK1'])


def test_rare_refs_collapse():
    # File with a wrong currency
    name = 'rare_refs_collapse'
    run_test_check(name, 'rare_refs', name, price=False)


def test_rare_refs_no_collapse():
    # File with a wrong currency, disable collapse
    name = 'rare_refs_no_collapse'
    run_test_check(name, 'rare_refs', name, extra=['--no_collapse'], price=False)


def test_octopart_1p():
    name = 'octopart_1'
    run_test_check(name + 'p', name, name + 'p', extra=['--octopart_key', OCTOPART_KEY, '--octopart_level', '4p'], config_file='octopart_no_cache.yaml')


def test_octopart_1n():
    name = 'octopart_1'
    run_test_check(name + 'n', name, name + 'n', config_file='octopart_no_cache.yaml')


def test_octopart_1_ambi():
    name = 'octopart_1_ambi'
    run_test_check(name, extra=['--octopart_key', OCTOPART_KEY, '--octopart_level', '4p'], config_file='octopart_no_cache.yaml')
    check_errors([r'Using "Adafruit Industries" for manf#="4062"', r'Ambiguous manf#="4062" please use manf to select the right one, choices:'])


def test_octopart_2n():
    name = 'octopart_2'
    run_test_check(name + 'n', name, name + 'n', extra=['--disable_api', 'KitSpace'], config_file='octopart.yaml')


def test_337():
    # Test for issue #337
    run_test_check('test_337_UserFieldCombining', extra=['--field', 'Supplier'], price=False)


def test_mouser_1():
    test_name = 'mouser_1'
    fields = ['S1MN', 'S1PN', 'S2MN', 'S2PN']
    extra = ['--split_extra_fields'] + fields + ['-f'] + fields + ['--include', 'mouser']
    run_test_check(test_name, 'complex_multipart', test_name, extra=extra, config_file='mouser.yaml')


def test_element14_1():
    test_name = 'element14_1'
    extra = ['--include', 'farnell', 'newark']
    run_test_check(test_name, 'safelink_receiver', test_name, extra=extra, config_file='element14.yaml')


def test_tme_1():
    test_name = 'tme_1'
    extra = ['--include', 'tme']
    run_test_check(test_name, 'safelink_receiver', test_name, extra=extra, config_file='tme.yaml')


class TestKicost(unittest.TestCase):

    def setUp(self):
        pass

    def test_something(self):
        pass

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
