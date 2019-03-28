###############################################################################
# This program simulate an interrupt button for a led 
###############################################################################

# import the streams module, it is needed to send data around
import streams
button = BTN0
led = D23
pinMode(led,OUTPUT)

# open the default serial port, the output will be visible in the serial console
streams.serial()  
light = 0
# loop forever
while True:
     if( digitalRead(button) == 0):
        if(light==0):
            light=1
        elif(light==1):
            light=0
     if(light== 0):
        print("light off")
        digitalWrite(led,LOW)
     else:
         print("light on")
         digitalWrite(led,HIGH)
     sleep(1000)
