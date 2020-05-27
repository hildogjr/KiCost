#!/bin/bash
# Automatic test macro for KiCad.
# Use this script in linux to generate the spreadsheet based 
# a on the XML or CSV file the test folder. Use to validate and check errors
# for selected tests.
# Written by Hildo Guillardi Júnior
# Use in Linux or Microsoft Windows with bash capability

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
BOMs=()
OPTS=()
# Extract options
parsed_options=$(
  getopt -o hv -l no_price -- "$@"
) || exit
eval "set -- $parsed_options"
while [ "$#" -gt 0 ]; do
  case $1 in
    (--no_price) OPTS+=("$1") ; shift;;
    (-[hv]) shift;;  # Options without parameter
    #(-t) shift 2;;   # Option with parameter
    (--) shift; break;;
    (*) BOMs+=("$1"); echo FILES "${FILES[@]}"; shift; break;; #exit 1 # should never be reached.
  esac
done
BOMs+=("$*")
#echo OPTIONS "${OPTS[@]}"
#echo BOMs "${FILES[@]}"

echo 'This macro tests selected xml or csv BOM files in this folder'
cd $(dirname $0)

RESULT_PATH=result_test/
EXPECT_PATH=expected_test/
LOG_PATH=log_test/

# Create the target directory for test files to compare if needed
mkdir -p ${RESULT_PATH}
mkdir -p ${LOG_PATH}
# Remove previous results if any

RESULT=0

for eachBOM in "${BOMs[@]}" ; do
    echo "##### Testing file: $eachBOM"
    rm "${RESULT_PATH}${eachBOM%.*}.csv" >& /dev/null
    rm "${LOG_PATH}${eachBOM%.*}.log" >& /dev/null
    XLSFILE="${eachBOM%.*}.xlsx"
    rm "$XLSFILE" >& /dev/null

    if [[ ${eachBOM#*.} == "csv" ]] ; then
       echo kicost "${OPTS[@]}" -wi "$eachBOM" --debug=10 --eda csv
       kicost "${OPTS[@]}" -wi "$eachBOM" --debug=10 --eda csv >& "${LOG_PATH}$eachBOM".log
    else
       kicost "${OPTS[@]}" -wi "$eachBOM" --debug=10 >& "${LOG_PATH}$eachBOM".log
    fi
    # Convert Excel to CSV file to make simple verification
    xlsx2csv --skipemptycolumns "${eachBOM%.*}.xlsx" | egrep -i -v '(USD\(| date|kicost|Total purchase)' > "${RESULT_PATH}${eachBOM%.*}.csv"
    # RESULT counts the number of errors (non 0 exit is error)
    diff "${EXPECT_PATH}${eachBOM%.*}.csv" "${RESULT_PATH}${eachBOM%.*}.csv"
    RESULT=$(($RESULT + $?))
    echo ""
done

if [[ ${RESULT} == 0 ]] ; then
  echo "If you see this message all BOMs spreadsheet were created without error"
else
  echo "If you see this message there were some unexpected results"
fi
exit ${RESULT}
