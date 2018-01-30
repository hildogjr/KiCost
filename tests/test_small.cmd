REM BOMs="part_list_small.csv Indium_X2.xml multipart.xml NF6X_Testboard.xml StickIt-Hat.xml"
for %%f in (part_list_small.csv Indium_X2.xml multipart.xml NF6X_Testboard.xml StickIt-Hat.xml) do kicost -i %%f -wq --inc digikey mouser farnell

echo "If you see this message all BOMs spreadsheet was created without error"
