import paho.mqtt.client as mqtt 
import stmpy 
import logging 
from threading import Thread 
import json 
import time
from sense_hat import SenseHat
from MQTT_TOPICS import *




class ScooterLogic: 


    def __init__(self, name, component): 

        self._logger = logging.getLogger(__name__) 
        self.name = name 
        self.component = component 
        self.sense = SenseHat()
        self.sense.clear()

        self.latitude = 63.1
        self.longitude = 10.1
        self.is_in_use = False

        self.status = {"name": self.name, "latitude": self.latitude, "longitude": self.longitude, "in_use": self.is_in_use}
        #inital transition
        t0 = {"source": "initial", "target": "stopped"}

        # TRANSITIONS
        #charger transitions
        t1 = {"source": "stopped", "target": "respond_to_charge_request", "trigger": "would_you_like_to_charge"} 
        t2 = {"source": "respond_to_charge_request", "target": "final", "trigger": "5_percent", "effect": "show_5; say_goodbye"}
        t3 = {"source": "respond_to_charge_request", "target": "final", "trigger": "2_percent", "effect": "show_2; say_goodbye"}
        
        
        # 1Hz event
        trig_1Hz = {"source": "stopped", "target" : "stopped", "trigger": "timer_1Hz", "effect": "Hz_1_event"}

        # STATES
        respond_to_charge_request = {"name": "respond_to_charge_request","entry": "contemplate_charging"}


        self.stm = stmpy.Machine(name=name, transitions = [trig_1Hz, t0, t1, t2, t3], obj=self, states = [respond_to_charge_request]) 
        self.component.stm_driver.add_machine(self.stm)
        
    def show_5(self):
        x = (0, 255, 0) # Green
        b = (0, 0, 0) # Off
        
        
        # Set up where each colour will display
        creeper_pixels = [
            b, b, x, x, x, x, b, b,
            b, b, x, b, b, b, b, b,
            b, b, x, b, b, b, b, b,
            b, b, x, x, x, b, b, b,
            b, b, b, b, b, x, b, b,
            b, b, b, b, b, x, b, b,
            b, b, b, b, b, x, b, b,
            b, b, x, x, x, b, b, b
        ]
        self.sense.set_pixels(creeper_pixels)
        time.sleep(2)
        self.sense.clear()
        
    def show_2(self):
        x = (0, 0, 255) # Blue
        b = (0, 0, 0) # Off
        
        
        # Set up where each colour will display
        creeper_pixels = [
            b, b, b, x, x, x, b, b,
            b, b, x, b, b, b, x, b,
            b, b, b, b, b, b, x, b,
            b, b, b, b, b, b, b, b,
            b, b, b, b, x, x, b, b,
            b, b, b, x, b, b, b, b,
            b, b, x, b, b, b, b, b,
            b, b, x, x, x, x, x, b
        ]
        self.sense.set_pixels(creeper_pixels)
        time.sleep(2)
        self.sense.clear()
        
        
    def waiting_for_joystick_press_down(self):
        # Define some colours
        x = (255, 0, 0) # Red
        b = (0, 0, 0) # Off
        
        
        # Set up where each colour will display
        creeper_pixels = [
            b, b, b, x, x, b, b, b,
            b, b, x, b, b, x, b, b,
            b, b, b, b, b, x, b, b,
            b, b, b, b, x, b, b, b,
            b, b, b, x, b, b, b, b,
            b, b, b, x, b, b, b, b,
            b, b, b, b, b, b, b, b,
            b, b, b, x, b, b, b, b
        ]
 
        # Display these colours on the LED matrix
        self.sense.set_pixels(creeper_pixels)
    
        answer = False
        
        while not answer:
            for event in self.sense.stick.get_events():
                if(event.direction == 'middle'):
                    answer = True
                    self.component.mqtt_client.publish(TOPIC_RESPONSE_CHARGE, '''{"msg": "yes"}''') 
                    self.sense.clear()
        
        
    def contemplate_charging(self):
        
        # trying to make answer non_blocking
        thread = Thread(target=self.waiting_for_joystick_press_down)
        thread.start()
                    
                            
    def say_goodbye(self):
        self._logger.debug('"scooter1" STM is shutting down...')

    def Hz_1_event:
        msg = status
        

        self._logger.debug("scooter 1Hz")
        self.component.mqtt_client.publish(TOPIC_SCOOTER_STATUS, payload=json.dumps(msg))

class ScooterManager: 

    def on_connect(self, client, userdata, flags, rc): 
        self._logger.debug('MQTT connected to {}'.format(client)) 

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        self._logger.debug('Incoming message to topic {}'.format(msg.topic)) 

        try: 
            payload = json.loads(msg.payload.decode("utf-8")) 
        except Exception as err: 
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err)) 
            return 
        
        command = payload.get('msg') 
        
                
        # do stuff depending on what command you receive

        if topic == TOPIC_REQUEST_CHARGE:
            self._logger.debug('"scooter1" is prompted if it would like to be charged')
            self.stm_driver.send("would_you_like_to_charge", "scooter1")

        if topic == TOPIC_DISCOUNT:
            if command == "2%":
                self._logger.debug(f'scooter1" received 2 percent discount')
                self.stm_driver.send("2_percent", "scooter1") 
            
            if command == "5%":
                self._logger.debug(f'scooter1" received 5 percent discount')
                self.stm_driver.send("5_percent", "scooter1") 
 
        if command == "would_you_like_to_charge": 
            self._logger.debug('"scooter1" is prompted if it would like to be charged')
            self.stm_driver.send("would_you_like_to_charge", "scooter1") 
            
        if command == "5_percent":
            self._logger.debug(f'scooter1" received 5 percent discount')
            self.stm_driver.send("5_percent", "scooter1") 
            
        if command == "2_percent":
            self._logger.debug(f'scooter1" received 2 percent discount')
            self.stm_driver.send("2_percent", "scooter1") 
            
        if command == "terminate":
            self._logger.debug('"scooter1" STM termination request received')
            self.stm_driver.send("terminate", "scooter1") 
            
            
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
        self.mqtt_client.subscribe(MQTT_TOPIC_SCOOTER) 

        self.mqtt_client.subscribe(TOPIC_REQUEST_CHARGE) 
        # self.mqtt_client.subscribe(TOPIC_RESPONSE_CHARGE) 

        # start the internal loop to process MQTT messages 
        self.mqtt_client.loop_start() 

        # start the stmpy driver, without any state machines for now 
        self.stm_driver = stmpy.Driver() 
        self.stm_driver.start(keep_active=True) 
        self._logger.debug('Component initialization finished') 
        
        # initiate an instance of Scooter STM
        self._logger.debug('Initializing Scooter STM with name "scooter1"') 
        ScooterLogic("scooter1", self)
        
        
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


 
cm = ScooterManager() 
