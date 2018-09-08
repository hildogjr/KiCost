REM BOMs="part_list_small.csv Indium_X2.xml multipart.xml NF6X_Testboard.xml StickIt-Hat.xml"
for %%f in (300-010.xml Aeronav_R.xml BoulderCreekMotherBoard.xml "CAN Balancer.xml" Decoder.xml Indium_X2.xml LedTest.xml NF6X_TestBoard.xml RPi-Test.xml "RX LR lite.xml" Receiver_1W.xml StickIt-Hat-old.xml StickIt-Hat.xml StickIt-QuadDAC.xml StickIt-RotaryEncoder.xml TestParts.xml acquire-PWM.xml acquire-PWM_2.xml b3u_test.xml bbsram.xml fitting_test.xml kc-test.xml local_Indium_X2.xml multipart.xml multipart2.xml part_list_big.csv part_list_small.csv part_list_small_nohdr.csv safelink_receiver.xml single_component.xml test.xml test2.xml test3.xml) do kicost -i %%f -wq --inc digikey mouser farnell arrow

echo "If you see this message all BOMs spreadsheet was created without error"
 