#############################################################
#####                @              @                   #####
#####                        V                          #####
#############################################################

import threading 
import adc
import streams
from wireless import wifi
from espressif.esp32net import esp32wifi as wifi_driver
from zerynthapp import zerynthapp
import requests
import json
import i2c
from mqtt import mqtt
streams.serial()

#variable period time checking


#INITIALIZE ALL VARIABLE 

##### DEFINE THE ASSOCIATION PINS -> VARIABLE
status_led_2 = D19
photoresistor = A4
light = D22
pump = D23
hum_1 = A7
serbatoio = D4 
plant_saved = 0

#### DEFINE THE MAX VALUE REGISTERED WITH SENSORS
max_hum = 300  #SOIL MOISTURE IN OVER WET CONDITION
hum_base = 4095 #SOIL MOISTURE IN OVER DRY CONDITION

#### DEFINE THE INFO ABOUT THE CONNECTED DEVICE
uid='UT_Y6EegS1GpQ8oZYuR0eA'
token='lsQT60hIREuBrQRqmR-J2A'

#### DEFINE THE IP OF THE REST SERVER
URL = 'http://192.168.43.245:5000/plant/'

#### DEFINE THE STRUCTURE TO STORE THE REF. VALUE OF A PLANT CATEGORY
plant_range= {
    'name':'null',
    'min_light':0,
    'min_hum':0,
    'max_hum':0
}

#### DEFINE THE PIN MODE 
pinMode(serbatoio,INPUT_PULLUP)
pinMode(light,OUTPUT)
pinMode(pump,OUTPUT)
pinMode(status_led_2,OUTPUT)

#### SET RELAY
digitalWrite(light,HIGH)
digitalWrite(pump,HIGH)

#### DEFINE ATTUATOR STATE ( 0: OFF | 1: ON )
pump_state = 0
light_state = 0

#### DEFINE WATER SILOS STATE ( 0: FULL | 1:EMPTY )
fuel = 0

#### DEFINE WORK MODE ( 0: AUTOMATIC | 1: MANUAL )
work_mod=0

#### DEFINE THE STATE OF THREAD
start_thread_1 = 0
start_thread_2 = 0
htu21_thread_start = 0
stop_stats = 0

############################################################################
######################@@BOARD FUNCTION@@####################################
############################################################################

def is_plant_saved(*args):
    global plant_saved
    print(' LOG | BOARD | checking saved preset')
    if(plant_saved == 0):
        print(' LOG | BOARD | no preset saved')
    else:
        print(' LOG | BOARD | yes ->')
        print(' LOG | BOARD | PRESET |  ->',plant_range['name'])
        print(' LOG | BOARD | PRESET |  ->',plant_range['min_light'])
        print(' LOG | BOARD | PRESET |  ->',plant_range['max_hum'])
        print(' LOG | BOARD | PRESET |  ->',plant_range['min_hum'])
    return plant_saved
    
def plant_selected(value):
    global URL, plant_range,plant_type        
    uri = URL+str(value)
    uri = uri.replace(" ","")
    print(' LOG | REST | SEND REQUEST TO : ',uri)
    result=requests.get(uri)                        #GET REQUEST TO REST SERVER
    data=json.loads(result.text())
    plant_range['name']=data['name']
    plant_range['min_light']=data['light_min']
    plant_range['max_hum']=data['hum_max']
    plant_range['min_hum']=data['hum_min']
    plant_type = value
    print(' LOG | REST | PLANT PRESET LOADED ON BOARD ',)
    print(' LOG | BOARD | PRESET |  ->',plant_range['name'])
    print(' LOG | BOARD | PRESET |  ->',plant_range['min_light'])
    print(' LOG | BOARD | PRESET |  ->',plant_range['max_hum'])
    print(' LOG | BOARD | PRESET |  ->',plant_range['min_hum'])
    
    
############################################################################

#HTU21/SHT21/SI7021 FUNCTION 
def my_init():
    global port
    port=i2c.I2C(I2C0, 0x40) #0x40 default address of htu21/sht21/si7021
    port.start()
    print('I2C PORT STARTED')

def init_HTU21D(my_p):
    # sensor software reset 
    my_p.write([0xFE])  
    sleep(500)
    #send the command for enabling the sampling mode for humidity and temperature (0 -> 12bit for RH and 14 bits for T)
    my_p.write([0xE6])
    my_p.write([0x00])
    
def build_value(lo,hi):
    return (lo << 8 | (hi & 0xFC)) #shift on left(8bits) of LO + set 0 on status bit "LAST 2 BITS OF HI"
           #(lo + 00000000)+(hi * 11111100)

##############################################################################

# MAPPING VALUE INTO A RANGE 
def remap( x, oMin, oMax, nMin, nMax ):
    #check reversed input range
    reverseInput = False
    oldMin = min( oMin, oMax )
    oldMax = max( oMin, oMax )
    if not oldMin == oMin:
        reverseInput = True
    #check reversed output range
    reverseOutput = False   
    newMin = min( nMin, nMax )
    newMax = max( nMin, nMax )
    if not newMin == nMin :
        reverseOutput = True
    portion = (x-oldMin)*(newMax-newMin)/(oldMax-oldMin)
    if reverseInput:
        portion = (oldMax-x)*(newMax-newMin)/(oldMax-oldMin)
    result = portion + newMin
    if reverseOutput:
        result = newMax - portion
    return result 
    
###################################################################

########################### THREAD 

#1  LIGHT MANAGER
def thread_light(name):
    global start_thread_1
    print(' LOG | THREAD | THREAD LIGHT STARTED')
    start_thread_1=1
    while(True):
        if work_mod == 0:
            turn_light(0) #CHECK LIGHT INTENSITY WITH LIGHT OFF
            value=read_light()
            print(' LOG | THREAD | THREAD PUMP | light value: ',value)
            if value < int(plant_range['min_light']):
                sleep(1000)
                turn_light(1)
        sleep(60000)

#2 PUMP MANAGER
def thread_pump(name):
    global start_thread_2,fuel,pump
    irrigation_progress = 0
    print(' LOG | THREAD | THREAD PUMP STARTED')
    start_thread_2 = 1
    while True:
        if work_mod == 0:
            value=read_hum()
            print(' LOG | THREAD | THREAD PUMP | hum value: ',value)
            fuel = is_empty()
            if (value < int(plant_range['min_hum'])):
                while ((value < int(plant_range['max_hum'])) and (fuel == 0) and work_mod==0):
                    turn_pump(1)
                    value=read_hum()
                    fuel = is_empty()
                    irrigation_progress = 1
                    sleep(500)
                if(fuel == 1) and (irrigation_progress == 1):
                    zapp.notify("ATTENTION",'Irrigation may have been interrupted due to insufficient water in the tank!')
            turn_pump(0)
        sleep(5000)

#3 STATS MANAGER
def thread_stats(name):
    client = mqtt.Client("stats",True)
   # client.set_will("UNISA/IOT/Gruppo_17/hum", '0', 2, False)
   # client.set_will("UNISA/IOT/Gruppo_17/light", '0', 2, False)
    for retry in range(3):
        try:
            client.connect("broker.hivemq.com",60)
            break
        except Exception as e:
            print(e)
            print(" LOG | MQTT | re-connecting...", retry)
    if retry>=2:
        print(' LOG | MQTT | impossible to connect mqtt server')
        while True:
            sleep(10000)
    print(" LOG | MQTT | connected to MQTT server.")
    client.loop()     # start the mqtt loop
    while(True):
        pinToggle(status_led_2)
        client.publish(str("UNISA/IOT/Gruppo_17/hum"), str(read_hum()), 2)
        sleep(5000)
        pinToggle(status_led_2)
        client.publish(str("UNISA/IOT/Gruppo_17/light"), str(remap(read_light(),0,4095,0,100)), 2)
        sleep(5000)
        
 # 4 HTU THREAD FOR TEMP E HUM OF AMBIENT
def htu21_thread(name):
    global htu21_thread_start
    htu21_thread_start = 1
    while True:
        event_sender(4,read_temp()) 
        sleep(200)
        event_sender(2,read_hum_amb()) 
        sleep(200)
        sleep(600000) #EVERY 10 MINUTES
        
####################################################################################

# FUNCTION USED TO RETREIVE DATA FROM SENSOR

#SOIL HUMIDITY
def read_hum():
    global hum_1,max_hum,hum_base
    raw_value = analogRead(hum_1)
    return remap(raw_value,hum_base,max_hum,0,100)
    
    
#REED SWITCH ON WATER SILOS
def is_empty():
    global serbatoio
    temp = digitalRead(serbatoio)
    return temp
    
#PHOTORESISTOR
def read_light():
    global photoresistor
    value = analogRead(photoresistor)
    return value
    
#AMBIENT TEMPERATURE 
def read_temp():
    global port
    port.write(0xE3)
    sleep(66)
    data=port.read(2)             #MSB     #LSB
    temp_raw_value = build_value(data[0], data[1])
    return int(((175.72*temp_raw_value)/(65536))-46.85) #CONVERSION FORMULA (READ DATASHEET)
     
#AMBIENT HUMIDITY
def read_hum_amb():
    global port
    port.write(0xE5)
    sleep(20)
    data=port.read(2)              #MSB     #LSB
    humid_raw_value = build_value(data[0], data[1])
    return int(((125*humid_raw_value)/(65536))-6)   #CONVERSION FORMULA (READ DATASHEET)

#########################################################

# FUNCTION THAT INTERACT WITH ATTUATOR

def turn_light(value):
    global light_state
    if value == 1 and light_state == 0:
        digitalWrite(light,LOW)
        light_state = 1
        event_sender(6,1)
    elif value == 0 and light_state == 1:
        digitalWrite(light,HIGH)
        light_state=0
        event_sender(6,0)
    elif value == 1 and light_state == 1:
        sleep(200)
    return light_state  

def turn_pump(value):
    global pump_state
    if value == 1 and pump_state == 0:
        digitalWrite(pump,LOW)
        pump_state = 1
        event_sender(7,1)
    elif value == 0 and pump_state == 1:
        digitalWrite(pump,HIGH)
        pump_state=0
        event_sender(7,0)
    elif value == 1 and pump_state == 1:
        sleep(200)
    return pump_state    

#FUNCTION THAT DEFINE THE "MODUS OPERANDI" OF BOARD
def change_work_mode(value):
    global work_mod
    work_mod=value
    
###########################################################################
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@#
###########################################################################
# THESE ARE THE 2 FUNCTIONS THAT CREATE AN INTERFACE TO THE ZERYNTH APP   #
#                                                                         #
# EVENT_SENDER: SEND TO THE ZERYNTH APP THE CODE OF AN EVENT AND ITS VALUE#
# EVENT CODIFICATION                                                      #
#               1 - INFORMATION ABOUT PHOTORESISTOR                       #
#               2 - INFORMATION ABOUT AMBIENT HUMIDITY                    #
#               3 - INFORMATION ABOUT SILOS STATE                         #
#               4 - INFORMATION ABOUT AMBIENT TEMPERATURE                 #
#               5 - INFORMATION ABOUT SOIL HUMIDITY                       #
#               6 - INFORMATION ABOUT THE STATE OF LED LIGHT              #
#               7 - INFORMATION ABOUT THE STATE OF THE PUMP               #
#               8 - OTHER                                                 #
#                                                                         #
#                                                                         #
# EVENT_RECEIVER: RECEIVE WITH THE SAME FORMAT OF EVENT_SENDER INFORMATION#
#                 ABOUT EVERY REQUEST FROM THE APP                        #
# EVENT CODIFICATION                                                      #
#               1 - REQUEST TO SET A PLANT DEFAULT RANGE VALUES           #
#               2 - REQUEST TO SET THE LIGHT                              #
#               3 - REQUEST TO SET THE PUMP                               #
#               4 - REQUEST TO FORCE UPDATE OF SENSORS AND STATE VALUES   #
#               5 - REQUEST TO CHECK IF OTHER PLANT WAS SAVED IN THE PAST #
#               99 - REQUEST TO CHANGE THE WORK MODE OF BOARD             #
#                                                                         #
###########################################################################

def event_sender(type,value):
    print(' LOG | SENT | event: ',type, ' value: ',value)
    zapp.event({'type': type,'value' : value})
    print(' LOG | EVENT SENT')
    
    
def event_receiver(*args):
    global plant_saved,fuel
    print(' LOG | event received: ',args[0],' value: ',args[1])
    
    if args[0]==1:  
        print(' LOG | REQUEST | SET PLANT')
        plant_selected(args[1])
        plant_saved=1
    
    if args[0]==2: 
        print(' LOG | REQUEST | SET PUMP: ',args[1])
        state = turn_light(args[1])
        return state
        
    if args[0]==3: 
        print(' LOG | REQUEST | SET PUMP : ',args[1])
        turn_pump(args[1])
    
    if args[0]==4: 
        print(' LOG | REQUEST | FORCE UPDATE')
        event_sender(1,read_light()) 
        sleep(500)
        event_sender(2,read_hum_amb()) 
        sleep(500)
        event_sender(3,is_empty()) 
        sleep(500)
        event_sender(4,read_temp()) 
        sleep(500)
        event_sender(5,int(read_hum())) 
        sleep(500)
        event_sender(6,light_state) 
        sleep(500)
        event_sender(7,pump_state) 
        sleep(500)
    
    if args[0]==5: 
        print(' LOG | REQUEST | check if plant preset was saved')
        event_sender(8,is_plant_saved())
        
    if args[0]==99:
        change_work_mode(args[1])
        
#################################################################
#################################################################

# BEGIN
print(' LOG | BOARD | Start')
try:
    global port
    my_init()             # START OF HTU21
    init_HTU21D(port)
    wifi_driver.auto_init()
    sleep(3000)
    
    for retry in range(20): 
        print(' LOG | BOARD | Connecting...')
        try:
            wifi.link('iPhone', wifi.WIFI_WPA2, 'ciaociao')
            print(' LOG | BOARD | Connected to wifi')
            break
        except IOError:
            sleep(1000)
    sleep(1000)
    print(' LOG | BOARD | Connecting to Zerynth App...')
    zapp = zerynthapp.ZerynthApp(uid, token)
    print(' LOG | BOARD | zapp object created!')
    
    
    # ZERYNTH APP ASSOCIATION FUNCTION
    
    zapp.on('event',event_receiver)
    zapp.on('is_saved',is_plant_saved)
    
    
    print(' LOG | BOARD | Start the app instance...')
    zapp.run()
    print(' LOG | BOARD | Instance started.')
    thread(thread_stats,'Nome')
    
   
    i=0
    while True:
        while(plant_saved == 0):
            pinToggle(status_led_2)
            sleep(1000)
        sleep(1000)
        event_sender(1,read_light()) 
        sleep(1000)
        event_sender(3,is_empty()) 
        sleep(1000)
        event_sender(5,int(read_hum())) 
        sleep(1000)
        event_sender(6,light_state) 
        sleep(1000)
        event_sender(7,pump_state) 
        sleep(1000)
        if htu21_thread_start == 0:
            thread(htu21_thread,'Hello')
        if start_thread_1 == 0:
            thread(thread_light,'Hello')
        sleep(1000)
        if start_thread_2 == 0:  
            thread(thread_pump,'Hello')
        sleep(60000) #ogni 60 sec si aggiorna

except Exception as e:
    print(e)
    
    