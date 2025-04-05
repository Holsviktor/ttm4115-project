import paho.mqtt.client as mqtt 
import stmpy 
import logging 
from threading import Thread 
import json 
import RPi.GPIO as GPIO
import time
import sys
from MQTT_TOPICS import *
 

# CONSTANS
PIN_MOTION = 13

# Triggers

TRIGGER_SCOOTER_DETECTED = "ask_if_scooter_wants_to_charge"

TRIGGER_CHARGE_ACCEPTED = "chargeaccepted"
TRIGGER_CHARGE_DENIED = "charge_denied"



class ChargerLogic: 


    def __init__(self, name, component): 

        self._logger = logging.getLogger(__name__) 
        self.name = name 
        self.component = component 

        self.latitude = 63
        self.longitude = 10

        self.id = name
        self.is_in_use = False
        self.state = "state_searching"

        #TRANSITIONS
        #inital transition
        inital_transiton = {"source": "initial", "target": "state_searching"}


        # "function": self.give_discount_5
        
        #searching transitions
        t1 = {"source": "state_searching", "target": "state_wait_for_scooter_charge_resposne", "trigger": TRIGGER_SCOOTER_DETECTED} 
        #t4 = {"source": "state_searching", "target": "final", "trigger":"terminate", "effect" : "say_goodbye"}

        #waiting transitions
        #timeout 
        trans_waiting_timeout = {"source": "state_wait_for_scooter_charge_resposne", "target": "state_searching", "trigger": "ask_scooter_request_timer", "effect": "give_discount_2"} 
        t3 = {"source": "state_wait_for_scooter_charge_resposne", "target": "state_chargeing", "trigger": TRIGGER_CHARGE_ACCEPTED, "effect": "give_discount_5"} 
        
        #chargeing transitions

        # trig_1Hz = {"source": "state_searching", "target" : "state_searching", "trigger": "timer_1Hz", "effect": "Event_1Hz"}
         
        # STATES
        state_searching = {"name": "state_searching", "entry": "state_searching"}
        state_wait_for_scooter_charge_resposne = {"name": "state_wait_for_scooter_charge_resposne", "entry": "state_wait_for_scooter_charge_resposne", "exit": "stop_timer('ask_scooter_request_timer')", "effect": "start_timer('ask_scooter_request_timer', '30000')"}
        state_chargeing = {"name": "state_chargeing", "entry": "state_chargeing", "exit": "state_chargeing_exit"}

        

        self.stm = stmpy.Machine(name=name, transitions = [inital_transiton, t1, trans_waiting_timeout, t3], obj=self, states = [state_searching, state_wait_for_scooter_charge_resposne, state_chargeing]) 
        self.component.stm_driver.add_machine(self.stm) 

        thread_1Hz = Thread(target=self.Event_1Hz)
        thread_1Hz.start()
   
    def Event_1Hz(self):

        # runs in its own thread and sleeps one second 
        time.sleep(1)

        msg = {"latitude": self.latitude, "longitude": self.longitude, "in_use": self.is_in_use, "state": self.state}
        
        self._logger.debug("Charger 1Hz")
        self.component.mqtt_client.publish(TOPIC_CHARGER_STATUS, payload=json.dumps(msg))


    def start_chargeing(self):
        self._logger.debug("CHARGER entered chargeing")
        self.state = "state_chargeing"

        self.is_in_use = True

    def start_chargeing_exit(self):
        self._logger.debug("CHARGER left chargeing")

        self.is_in_use = False
    
    def state_wait_for_scooter_charge_response(self):
        self._logger.debug("Charger neterted state waiting for scooter response")
        self.state = "state_wait_for_scooter_charge_response"

        self.component.mqtt_client.publish(TOPIC_REQUEST_CHARGE, '''{"msg": "found_scooter"}''') 

    #def state_wait_for_scooter_charge_response_exit(self): 
    #    self._logger.debug("Charger leaving state wait for scooter charge response")
        
    def give_discount_2(self):
        self.component.mqtt_client.publish(TOPIC_DISCOUNT, '''{"msg": "2%"}''') 
    
    def give_discount_5(self):
        self.component.mqtt_client.publish(TOPIC_DISCOUNT, '''{"msg": "5%"}''') 
        
    

    def say_goodbye(self):
        self._logger.debug('"charger1" STM is terminating...')
        # self.component.mqtt_client.publish(MQTT_TOPIC_CHARGER, '''{"msg": "turn_off"}''')
    
    def send_message_to_scooter(self):
        self._logger.debug("send message scooter")
        # ask scooter if it needs to be charged
        self.component.mqtt_client.publish(TOPIC_REQUEST_CHARGE, '''{"msg": "1"}''')

    def state_searching(self):
        self._logger.debug("Charger entered state searching")
        self.state = "state_searching"

        # trying to make state_searching non-blocking
        thread = Thread(target=self.measure_distance)
        thread.start()

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
        
        self._logger.debug("CHARGER sensed movement")

        # moves stm to waiting for scooter repsonse
        self.component.stm_driver.send(TRIGGER_SCOOTER_DETECTED, "charger1")
        # notify yourself that you found a scooter to trigger a transition 
        # self.component.mqtt_client.publish(TOPIC_MOVEMNT, '''{"msg": "found_scooter"}''') 
       
 

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
        topic = msg.topic
        
                
        # do stuff depending on what command you receive

        if command == "found_scooter": 
            self._logger.debug('"charger1" has registered scooter movement')
            self.stm_driver.send("found_scooter", "charger1") 
            
        if topic == TOPIC_RESPONSE_CHARGE:
            if command == "yes":
                self._logger.debug('Scooter has confirmed charging')
                self.stm_driver.send(TRIGGER_CHARGE_ACCEPTED, "charger1")
            if command == "no":
                self._logger.debug("Scooter denied chargeing, entering search")
                self.stm_driver.send(TRIGGER_CHARGE_DENIED, "charger1")
                
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

        self.mqtt_client.subscribe(TOPIC_REQUEST_CHARGE) 
        self.mqtt_client.subscribe(TOPIC_RESPONSE_CHARGE)

        self.mqtt_client.subscribe(TOPIC_END_CHARGE) 

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
