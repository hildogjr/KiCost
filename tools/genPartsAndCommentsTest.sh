#!/bin/bash
FIELDS="mpn pn p# part_num part-num part# manf_num manf-num manf# man_num man-num man# mfg_num mfg-num mfg# mfr_num mfr-num mfr# mnf_num mnf-num mnf#"
TEST_DESC="All possible part nbr fields and comments"
TEST_SRC=$(tr " " "-"<<<"${TEST_DESC}")
DATE=$(date +%Y-%m-%d)

cat << EOFILEHEAD
<?xml version="1.0" encoding="UTF-8"?>
<export version="D">
  <design>
    <source>/${TEST_SRC}.sch</source>
    <date>2021-01-02</date>
    <tool>Eeschema 5.1.9+dfsg1-1</tool>
    <sheet number="1" name="/" tstamps="/">
      <title_block>
        <title>${TEST_DESC}</title>
        <company>KiCOST TEST</company>
        <rev></rev>
        <date>${DATE}</date>
        <source>manual_edit</source>
        <comment number="1" value=""/>
        <comment number="2" value=""/>
        <comment number="3" value=""/>
        <comment number="4" value=""/>
      </title_block>
    </sheet>
  </design>
  <components>
EOFILEHEAD

idx=1
for i in $FIELDS ; do

  cat << EOHEAD
    <comp ref="C${idx}">
      <value>${idx}nF</value>
      <datasheet></datasheet>
      <fields>
EOHEAD


  for j in $FIELDS ; do
     if [ $i == $j ] ; then
        val=$(tr '#' '_' <<<"Field-${j}")
cat << EOCOMMENT
        <field name="comment">Field '$j' is '$val'</field>
EOCOMMENT
     else
        val=
     fi # $i == $j
     cat << EOFIELD
        <field name="${j}">$val</field>
EOFIELD
  done # for j

  cat <<  EOEND
      </fields>
    </comp>
EOEND

  idx=$((idx+1))
done # for i

cat << 'EOFILEEND'
  </components>
</export>
EOFILEEND

