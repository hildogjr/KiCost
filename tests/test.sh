# Automatic test macro for KiCad.
# Use this script in linux to generate the spreadsheet based on the XML files of this folder after changes in the KiCost python module. Use to validate and check erros.
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

echo 'This macro test all the xml files BOM in this folder'
cd $(dirname $0)

RESULT_PATH=result_test/
EXPECT_PATH=expected_test/
# Create the target directory for test files to compare if needed
mkdir -p ${RESULT_PATH}
# Remove previous results if any
rm ${RESULT_PATH}* >& /dev/null

RESULT=0

# Find BOMs
BOMs=$(find *.csv *.xml)

# Compute BOMs
while read -r eachBOM; do
  ./test_single.sh --noprice "$eachBOM"
  RESULT=$(($RESULT + $?))
done <<< "$BOMs"

# Display final result
if [[ ${RESULT} == 0 ]] ; then
  echo "If you see this message all BOMs spreadsheet was created without error"
else
  echo "If you see this message there were some unexpected results"
fi
exit ${RESULT}
