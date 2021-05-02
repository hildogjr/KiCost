#!/bin/bash -xv
#kicost --no_price --variant variant1 -wi variants_3.xml --debug=10

$(dirname $0)/test_single.sh --no_price variants_3.xml
$(dirname $0)/test_single.sh --no_price --variant variant1 variants_3.xml
#cat log_test/variants_3.xml.log

