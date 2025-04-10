import paho.mqtt.client as mqtt 
import stmpy 
import logging 
from threading import Thread 
import json 
import RPi.GPIO as GPIO
import time
import sys
 
MQTT_BROKER = 'mqtt20.iik.ntnu.no' 
MQTT_PORT = 1883 

MQTT_TOPIC_SCOOTER = '10/scooter' 
MQTT_TOPIC_CHARGER = '10/charger'


PIN_MOTION = 13


class ChargerLogic: 


    def __init__(self, name, component): 

        self._logger = logging.getLogger(__name__) 
        self.name = name 
        self.component = component 

        #charger state machine transitions
        t0 = {"source": "initial", "target": "searching"}
        t1 = {"source": "searching", "target": "would_you_like_to_charge", "trigger": "found_scooter", "effect": "send_message_to_scooter"} 
        t2 = {"source": "would_you_like_to_charge", "target": "searching", "trigger": "t0", "effect": "give_discount_2"} 
        t3 = {"source": "would_you_like_to_charge", "target": "searching", "trigger": "yes_charge", "effect": "give_discount_5"} 
        t4 = {"source": "searching", "target": "final", "trigger":"terminate", "effect" : "say_goodbye"}
        
        
        # entry actions
        searching = {"name": "searching", "entry": "start_measurement"}
        would_you_like_to_charge = {"name": "would_you_like_to_charge", "entry": "start_timer('t0', '30000')", "exit": "stop_timer('t0')"}
        

        self.stm = stmpy.Machine(name=name, transitions = [t0, t1, t2, t3, t4], obj=self, states = [searching, would_you_like_to_charge]) 
        self.component.stm_driver.add_machine(self.stm) 
        
    def say_goodbye(self):
        self._logger.debug('"charger1" STM is terminating...')
        # self.component.mqtt_client.publish(MQTT_TOPIC_CHARGER, '''{"msg": "turn_off"}''') 
                
    def send_message_to_scooter(self):
        # ask scooter if it needs to be charged
        self.component.mqtt_client.publish(MQTT_TOPIC_SCOOTER, '''{"msg": "would_you_like_to_charge"}''') 
        
    def give_discount_2(self):
        self.component.mqtt_client.publish(MQTT_TOPIC_SCOOTER, '''{"msg": "2_percent"}''') 
    
    def give_discount_5(self):
        self.component.mqtt_client.publish(MQTT_TOPIC_SCOOTER, '''{"msg": "5_percent"}''') 
        
    def measure_distance(self):

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        #Config Pins
        #Input
        GPIO.setup(PIN_MOTION, GPIO.IN)

        scooter_found = False
        
        self._logger.debug('"charger1" searches for scooter movement...')
        
        while(not scooter_found):
            if GPIO.input(PIN_MOTION):
                scooter_found = True
                    
        GPIO.cleanup()
        
        # notify yourself that you found a scooter to trigger a transition 
        self.component.mqtt_client.publish(MQTT_TOPIC_CHARGER, '''{"msg": "found_scooter"}''') 
        
        
    def start_measurement(self):
        # trying to make searching non-blocking
        thread = Thread(target=self.measure_distance)
        thread.start()

class ChargerManager: 

    def on_connect(self, client, userdata, flags, rc): 
        self._logger.debug('MQTT connected to {}'.format(client)) 

    def on_message(self, client, userdata, msg): 
        self._logger.debug('Incoming message to topic {}'.format(msg.topic)) 

        try: 
            payload = json.loads(msg.payload.decode("utf-8")) 
        except Exception as err: 
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err)) 
            return 
        
        command = payload.get('msg') 
        
                
        # do stuff depending on what command you receive

        if command == "found_scooter": 
            self._logger.debug('"charger1" has registered scooter movement')
            self.stm_driver.send("found_scooter", "charger1") 
            
        if command == "yes_charge":
            self._logger.debug('Scooter has confirmed charging')
            self.stm_driver.send("yes_charge", "charger1") 
            
        if command == "terminate":
            self._logger.debug('"charger1" STM termination request received')
            self.stm_driver.send("terminate", "charger1") 
            
            
    def __init__(self): 

        self._logger = logging.getLogger(__name__) 
        print('logging under name {}.'.format(__name__)) 
        self._logger.info('Initializing MQTT client') 

        # create a new MQTT client 
        self.mqtt_client = mqtt.Client() 

        # callback methods 
        self.mqtt_client.on_connect = self.on_connect 
        self.mqtt_client.on_message = self.on_message 

        # Connect to the broker 
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT)) 
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT) 

        # subscribe to proper topic(s) of your choic 
        self.mqtt_client.subscribe(MQTT_TOPIC_CHARGER) 

        # start the internal loop to process MQTT messages 
        self.mqtt_client.loop_start() 

        # start the stmpy driver, without any state machines for now 
        self.stm_driver = stmpy.Driver() 
        self.stm_driver.start(keep_active=True) 
        self._logger.debug('Component initialization finished') 
        
        # initiate an instance of Charger stm, call it "charger1"
        self._logger.debug('Initializing Charger STM with name "charger1"') 
        ChargerLogic("charger1", self)
        
        
    def stop(self): 
        # stop the MQTT client 
        self.mqtt_client.loop_stop() 
        # stop the state machine Driver 
        self.stm_driver.stop() 


debug_level = logging.DEBUG 
logger = logging.getLogger(__name__) 
logger.setLevel(debug_level) 
ch = logging.StreamHandler() 
ch.setLevel(debug_level) 
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s') 
ch.setFormatter(formatter) 
logger.addHandler(ch) 


 
cm = ChargerManager() 
