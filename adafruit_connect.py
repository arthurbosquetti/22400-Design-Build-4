# The MIT License (MIT)
# Copyright (c) 2019 Mike Teachman
# https://opensource.org/licenses/MIT
#
# Example MicroPython and CircuitPython code showing how to use the MQTT protocol with Adafruit IO, to  
# publish and subscribe on the same device
#
# Tested using the releases:
#   ESP8266
#       MicroPython 1.9.3
#       MicroPython 1.9.4
#       MicroPython 1.10
#       CircuitPython 2.3.1     (needs addition of CircuitPython specific umqtt module)
#       CircuitPython 3.0.0     (needs addition of CircuitPython specific umqtt module)
#   ESP32
#       MicroPython 1.9.4       (needs addition of MicroPython umqtt module)
#       MicroPython 1.10
#
# Tested using the following boards:
#   Adafruit Feather HUZZAH ESP8266
#   Adafruit Feather HUZZAH ESP32
#   WeMos D1 Mini
#
# User configuration parameters are indicated with "ENTER_".  

import network
import utime
from umqtt.robust import MQTTClient
import os
import gc
import sys

# Sleep for 10s to be able to save the data...
print("Sleeping for 10 sec...")
utime.sleep(10)

# the following function is the callback which is 
# called when subscribed data is received
def cb(topic, msg):
    print('Subscribe:  Received Data:  Topic = {}, Msg = {}\n'.format(topic, msg))
    # free_heap = int(str(msg,'utf-8'))

# WiFi connection information
WIFI_SSID = 'Arthur iPhone'
WIFI_PASSWORD = 'aviaodepapel'

# turn off the WiFi Access Point
ap_if = network.WLAN(network.AP_IF)
ap_if.active(False)

# connect the device to the WiFi network
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(WIFI_SSID, WIFI_PASSWORD)

# wait until the device is connected to the WiFi network
MAX_ATTEMPTS = 20
attempt_count = 0
while not wifi.isconnected() and attempt_count < MAX_ATTEMPTS:
    attempt_count += 1
    utime.sleep(3)

if attempt_count == MAX_ATTEMPTS:
    print('could not connect to the WiFi network')
    sys.exit()

# create a random MQTT clientID 
random_num = int.from_bytes(os.urandom(3), 'little')
mqtt_client_id = bytes('client_'+str(random_num), 'utf-8')

# connect to Adafruit IO MQTT broker using unsecure TCP (port 1883)
# 
# To use a secure connection (encrypted) with TLS: 
#   set MQTTClient initializer parameter to "ssl=True"
#   Caveat: a secure connection uses about 9k bytes of the heap
#         (about 1/4 of the micropython heap on the ESP8266 platform)
ADAFRUIT_IO_URL = b'io.adafruit.com' 
ADAFRUIT_USERNAME = b'arthurbosquetti'
ADAFRUIT_IO_KEY = b'aio_tMvu464InpmhOZEjDl2Dnx8cJZhI'
ADAFRUIT_IO_FEEDNAME = b'Temperature'

client = MQTTClient(client_id=mqtt_client_id, 
                    server=ADAFRUIT_IO_URL, 
                    user=ADAFRUIT_USERNAME, 
                    password=ADAFRUIT_IO_KEY,
                    ssl=False)
                    
try:            
    client.connect()
except Exception as e:
    print('could not connect to MQTT server {}{}'.format(type(e).__name__, e))
    sys.exit()

# publish free heap statistics to Adafruit IO using MQTT
# subscribe to the same feed
#
# format of feed name:  
#   "ADAFRUIT_USERNAME/feeds/ADAFRUIT_IO_FEEDNAME"
mqtt_feedname = bytes('{:s}/feeds/{:s}'.format(ADAFRUIT_USERNAME, ADAFRUIT_IO_FEEDNAME), 'utf-8')
client.set_callback(cb)      
client.subscribe(mqtt_feedname)  
PUBLISH_PERIOD_IN_SEC = 10 
SUBSCRIBE_CHECK_PERIOD_IN_SEC = 0.5 
accum_time = 0
temperature_data = 0

data_file = open("data_file.txt", "w")
data_file.close()

wifi_was_connected = True

while True:
    try:

        #print("accum_time = {}, wifi_was_connected = {}".format(accum_time, wifi_was_connected))

        # Publish
        if accum_time >= PUBLISH_PERIOD_IN_SEC:

            temperature_data += 1

            print("Saving data locally...")
            data_file = open("data_file.txt", "a")
            data_file.write("{} \n".format(temperature_data))
            data_file.close()

            # free_heap_in_bytes = gc.mem_free()
            # print('Publish:  freeHeap = {}'.format(free_heap_in_bytes))
            # client.publish(mqtt_feedname, bytes(str(free_heap_in_bytes), 'utf-8'), qos=0) 

            if wifi.isconnected():
                print("Publishing data online...")
                client.publish(mqtt_feedname, bytes(str(temperature_data), 'utf-8'), qos=0)
            else:
                print("Could not publish data online!")
            accum_time = 0                
        
        # Subscribe. Non-blocking check for a new message.  
        if wifi.isconnected() and wifi_was_connected:
            print("Checking for messages...")
            client.check_msg()
        elif wifi.isconnected() and not wifi_was_connected:
            print("trying to resubscribe the client...")
            try:            
                client.connect()
                print("client connected!")
                client.set_callback(cb) 
                print("callback set!")     
                client.subscribe(mqtt_feedname) 
                print("client subscribed!") 
                wifi_was_connected = True
                
            except Exception as e:
                print('could not connect to MQTT server {}{}'.format(type(e).__name__, e))
                # sys.exit()            

        # Avoid checking for new messages when disconnects
        if not wifi.isconnected():
            print("wifi is off")
            # client.disconnect()
            wifi_was_connected = False
        
        utime.sleep(SUBSCRIBE_CHECK_PERIOD_IN_SEC)
        accum_time += SUBSCRIBE_CHECK_PERIOD_IN_SEC

    except KeyboardInterrupt:
        print('Ctrl-C pressed...exiting')
        # client.disconnect()
        # sys.exit()
