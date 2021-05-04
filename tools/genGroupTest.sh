#!/bin/bash
COMPONENTS="C1 C2 C10 C20 C5"
TEST_DESC="Parts to test grouping, field ignore"
TEST_SRC=$(tr " ," "--"<<<"${TEST_DESC}")
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
for i in $COMPONENTS ; do

  VALUE="1nF"
  MANFN="COMP-${VALUE}"
  if [ $i == "C10" ] ; then
     VALUE="1uF"
  fi
  if [ $i == "C5" ] ; then
     MANFN="OTHERCOMP-${VALUE}"
  fi
  cat << EOHEAD
    <comp ref="${i}">
      <value>${VALUE}</value>
      <datasheet></datasheet>
      <fields>
EOHEAD
 
cat << EOCOMMENT
        <field name="manf#">${MANFN}</field>
        <field name="comment">Comment for '$i' with value '${VALUE}'</field>
EOCOMMENT

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

