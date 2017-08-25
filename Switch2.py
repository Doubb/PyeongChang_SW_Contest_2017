import RPi.GPIO as IoPort
import time
import translation_stt_tts
import chatting_en_to_ko

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

Sw1 = 25 # Number of gpio pin

IoPort.setmode(IoPort.BCM)
IoPort.setup(Sw1, IoPort.IN)

rcv = 0;

while True :
    rcv = IoPort.input(Sw1)

    if rcv == 1 :
        chatting_en_to_ko.main()
    
    time.sleep(0.1)

    IoPort.cleanup()

