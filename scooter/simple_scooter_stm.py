import threading
import paho.mqtt.client as mqtt 
import stmpy 
import logging 
from threading import Thread 
import json 
import time
from sense_hat import SenseHat
from MQTT_TOPICS import *
import SENSE_HAT_DEFINITIONS

# Triggers

GO_TO_CHARGE = "go_to_charge"
GO_TO_STOPPED = "go_to_stopped" 
GO_TO_LOCKED = "go_to_locked"

REQUEST_UNLOCK = "go_to_enabled"
class ScooterLogic: 


    def __init__(self, name, component): 

        self._logger = logging.getLogger(__name__) 
        self.name = name 
        self.component = component 
        self.sense = SenseHat()
        self.sense.clear()

        # position
        self.latitude = 63.1
        self.longitude = 10.1
        
        #status
        self.state = ""
        self.is_in_use = False
        self.state_of_charge = 50

        #thread
        self.joystick_thread = None
        self.stop_joystick_thread = False

        self.status = {"name": self.name, "latitude": self.latitude, "longitude": self.longitude, "in_use": self.is_in_use}
        #inital transition
        t0 = {"source": "initial", "target": "state_locked"}

        # TRANSITIONS
        #charger transitions
        #t1 = {"source": "state_stopped", "target": "state_respond_to_charge_request", "trigger": "ask_scooter_charge"} 

        #t2 = {"source": "state_respond_to_charge_request", "target": "stopped", "trigger": "5_percent", "effect": "helper_show_5; say_goodbye"}
        #t3 = {"source": "state_respond_to_charge_request", "target": "stopped", "trigger": "2_percent", "effect": "helper_show_2; say_goodbye"}
        
        transition_go_to_enabled_0 = {"source": "state_locked", "target": "state_enabled", "trigger": REQUEST_UNLOCK, "effect": ""}
        transition_go_to_enabled_1 = {"source": "state_chargeing", "target": "state_enabled", "trigger": REQUEST_UNLOCK, "effect": ""}

        transition_request_to_chargeing = {"source": "state_respond_to_charge_request", "target": "state_chargeing", "trigger": GO_TO_CHARGE, "effect": "helper_show_5; say_goodbye"}
        transition_request_to_locked = {"source": "state_respond_to_charge_request", "target": "state_locked", "trigger": GO_TO_LOCKED, "effect": "helper_show_2; say_goodbye"}
        
        
        # 1Hz event

        # STATES
        state_respond_to_charge_request = {"name": "state_respond_to_charge_request","entry": "state_respond_to_charge_request"}
        state_enabled = {"name": "state_enabled", "entry": "state_enabled", "exit": ""}
        state_locked = {"name": "state_locked", "entry": "state_locked", "exit": ""}
        state_chargeing = {"name": "state_chargeing", "entry": "state_chargeing", "exit": "stop_chargeing"}
        


        self.stm = stmpy.Machine(name=name, transitions = [t0, transition_go_to_enabled_0, transition_go_to_enabled_1, transition_request_to_chargeing, transition_request_to_locked], obj=self, states = [state_respond_to_charge_request, state_enabled, state_locked, state_chargeing]) 
        self.component.stm_driver.add_machine(self.stm)

        thread_1Hz = Thread.thread(target=self.Event_1Hz)
        thread_1Hz.start()
        



    def Event_1Hz(self):
        msg = self.status
        
        time.sleep(1)

        self._logger.debug("scooter 1Hz")
        self.component.mqtt_client.publish(TOPIC_SCOOTER_STATUS, payload=json.dumps(msg))


    def state_locked(self): 
        self._logger.debug("Entered state locked - idle state")

        self.is_in_use = False
        self.state = "locked"
    
    def state_enabled(self):
        self._logger.debug("Entered state stopped")

        self.is_in_use = True
        self.state = "enabled"

        if not self.joystick_thread or not self.joystick_thread.is_alive():
            self.stop_joystick_thread = False
            self.joystick_thread = threading.Thread(target=self._handle_joystick_input)
            self.joystick_thread.daemon = True
            self.joystick_thread.start() 

    def state_enabled_exit(self):
        self._logger.debug("Exiting state enabled")

        # Stop the joystick thread if it's running
        if self.joystick_thread and self.joystick_thread.is_alive():
            self.stop_joystick_thread = True
            self.joystick_thread.join()

        # Clear the display
        self.sense.clear()

        self._logger.debug("State disabled and display cleared")


    def state_chargeging(self):
        self._logger.debug("Entered state chargeing")
        
        self.is_in_use = True





        
    def state_respond_to_charge_request(self):

        self._logger.debug("Scooter contemplate charging")
        
        # trying to make answer non_blocking
        thread = Thread(target=self.thread_waiting_for_joystick_press_down)
        thread.start()
                    
                            
    def say_goodbye(self):
        self._logger.debug('"scooter1" STM is shutting down...')


    def thread_waiting_for_joystick_press_down(self):
 
        # Display these colours on the LED matrix
        self.sense.set_pixels(SENSE_HAT_DEFINITIONS.question_mark_pixels)
    
        answer = False
        

        start_time = time.time()
        while not answer or (time.time() < start_time + 30) :
            for event in self.sense.stick.get_events():
                if(event.direction == 'up'):
                    answer = True
                    self.component.mqtt_client.publish(TOPIC_RESPONSE_CHARGE, '''{"msg": "yes"}''') 
                    self.sense.clear()
                    self.component.stm_driver.send(GO_TO_CHARGE, f"{self.name}")
                    return
                if(event.direction == 'down'):
                    answer = True
                    self.component.mqtt_client.publish(TOPIC_RESPONSE_CHARGE, '''{"msg": "no"}''')
                    self.sense
                    self.component.stm_driver.send(GO_TO_STOPPED, f"{self.name}")
                    return
        
                
        self._logger.debug("Request to charge timout entering locked")

        self.component.mqtt_client.publish(TOPIC_RESPONSE_CHARGE, '''{"msg": "no"}''')
        self.sense()
        self.component.stm_driver.send(GO_TO_LOCKED, f"{self.name}")
        return
        
    def helper_show_5(self):
        self.sense.set_pixels(SENSE_HAT_DEFINITIONS.five_digit_pixels)
        time.sleep(2)
        self.sense.clear()
        
    def helper_show_2(self):
        self.sense.set_pixels(SENSE_HAT_DEFINITIONS.two_digit_pixels)
        time.sleep(2)
        self.sense.clear()
    
 
        
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
        self._logger.debug(f"Got topic: {topic} and msg: {msg}")

        if topic == TOPIC_REQUEST_UNLOCK:
            self._logger.debug('Scooter1 is requested to unlock')
            self.stm_driver.send("request_unlock", "scooter1")
        
        if topic == TOPIC_REQUEST_CHARGE:
            self._logger.debug('"scooter1" is prompted if it would like to be charged')
            self.stm_driver.send("ask_scooter_charge", "scooter1")

        if topic == TOPIC_DISCOUNT:
            if command == "2%":
                self._logger.debug(f'scooter1" received 2 percent discount')
                self.stm_driver.send("2_percent", "scooter1") 
            
            if command == "5%":
                self._logger.debug(f'scooter1" received 5 percent discount')
                self.stm_driver.send("5_percent", "scooter1") 
 
        if command == "ask_scooter_charge": 
            self._logger.debug('"scooter1" is prompted if it would like to be charged')
            self.stm_driver.send("ask_scooter_charge", "scooter1") 
            
        if command == "5%":
            self._logger.debug(f'scooter1" received 5 percent discount')
            self.stm_driver.send("5_percent", "scooter1") 
            
        if command == "2%":
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
        self.mqtt_client.subscribe(TOPIC_RESPONSE_CHARGE) 
        self.mqtt_client.subscribe(TOPIC_MOVEMNT) 

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
