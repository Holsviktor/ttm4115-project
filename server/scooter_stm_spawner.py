import paho.mqtt.client as mqtt 
import stmpy 
import logging 
import json 
import random
import sys
import time

MQTT_BROKER = 'mqtt20.iik.ntnu.no' 
MQTT_PORT = 1883 
MQTT_TOPIC_POSITIONS = '10/scooter_positions' 
MQTT_TOPIC_SERVER_REQUESTS = '10/server_request'
MQTT_TOPIC_MANAGER = '10/manager'

STATUS_FREE = 'free'
STATUS_BOOKED = 'booked'

class ScooterLogic: 

    def __init__(self, name, component, x, y): 

        self._logger = logging.getLogger(__name__) 
        self.name = name 
        self.component = component 
        # 'GPS coordinates are internal'
        self.x = x 
        self.y = y
        
        # scooter state machine transitions
        t0 = {'source': 'initial', 'target': 'is_free'}
        t1 = {'source': 'is_free', 'target': 'is_free', 'trigger': 'give_coordinates', 'effect': 'send_coordinates'} 
        t2 = {'source': 'is_free', 'target': 'final', 'trigger': 'abort', 'effect': 'say_goodbye'}
        t3 = {'source': 'is_free', 'target': 'in_use', 'trigger': 'confirm_booking', 'effect' : 'book_this'}
        t4 = {'source': 'in_use', 'target': 'in_use', 'trigger': 'confirm_booking', 'effect' : 'book_this'}
        t5 = {'source': 'in_use', 'target': 'final', 'trigger': 'abort', 'effect': 'say_goodbye'}
        t6 = {'source': 'in_use', 'target': 'is_free', 'trigger': 'stop_booking', 'effect' : 'end_trip'}
        
        # skip sending coordinates when scooter is booked, aka in_use
        in_use = {'name': 'in_use', 'give_coordinates' : ''} 
        
        self.stm = stmpy.Machine(name=name, transitions = [t0, t1, t2, t3, t4, t5, t6], obj=self, states = [in_use]) 
        self.component.stm_driver.add_machine(self.stm)
    
    # scooter ack to server that it is no longer booked
    def end_trip(self):
        ts = time.time()
        message = {'msg': 'ack_booking_finished','scooter_name' : self.name, 'timestamp': ts}
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_MANAGER, payload) 
    
    # scooter sends to server its coordinates   
    def send_coordinates(self):
        message = {'msg': 'coordinates','scooter_name' : self.name, 'x': self.x, 'y': self.y}
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_POSITIONS, payload) 
    
     # scooter ack to server that it is now booked
    def book_this(self):
        ts = time.time()
        message = {'msg': 'ack_booking','scooter_name' : self.name, 'timestamp': ts}
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_MANAGER, payload) 
      
    def say_goodbye(self):
        self._logger.debug(f'{self.name} says : GOODBYE!') 


class ScooterManager: 

    def on_connect(self, client, userdata, flags, rc): 
        self._logger.debug('Scooter MQTT connected to {}'.format(client)) 

    def on_message(self, client, userdata, msg): 
        
        try: 
            payload = json.loads(msg.payload.decode("utf-8")) 
        except Exception as err: 
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err)) 
            return 
        
        command = payload.get('msg') 
        
        self._logger.debug('SCOOTER Incoming message to topic {} : "{}" '.format(msg.topic, command) ) 
          
        # do stuff depending on what command you receive
        
        if command == 'give_coordinates':
            for stm_id in self.stm_driver._stms_by_id:
                # only collect coordinates from scooters that are not booked 
                self.stm_driver.send('give_coordinates', stm_id) 
                
        if command == 'abort':
            for stm_id in self.stm_driver._stms_by_id: 
                self.stm_driver.send('abort', stm_id)
            
        if command == 'confirm_booking':
            self.stm_driver.send('confirm_booking', payload.get('scooter_name'))
            
        if command == 'stop_booking':
            self.stm_driver.send('stop_booking', payload.get('scooter_name'))
            
                   
    def __init__(self, number_of_scooters_to_spawn): 
        
        self.scooters = []
        self._logger = logging.getLogger(__name__) 
        print('logging under name {}.'.format(__name__)) 
        self._logger.info('Initializing MQTT client') 

        # create a new MQTT client 
        self.mqtt_client = mqtt.Client() 

        # callback methods 
        self.mqtt_client.on_connect = self.on_connect 
        self.mqtt_client.on_message = self.on_message 

        # connect to the broker 
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT)) 
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT) 

        # subscribe to proper topic(s) of your choic 
        self.mqtt_client.subscribe(MQTT_TOPIC_SERVER_REQUESTS) 

        # start the internal loop to process MQTT messages 
        self.mqtt_client.loop_start() 

        # start the stmpy driver, without any state machines for now 
        self.stm_driver = stmpy.Driver() 
        self.stm_driver.start(keep_active=True) 
        self._logger.debug('Component initialization finished') 
        
        # initiates several instances of Scooter state machines
        for i in range(0, number_of_scooters_to_spawn):
            self._logger.debug(f'Initializing Scooter STM with name "scooter{i}"') 
            self.scooters.append(f'scooter{i}')
            random.seed = random.randint(0, 1337)
            ScooterLogic(f'scooter{i}', self, x = random.randint(0, 988), y = random.randint(0, 661))
        
        
    def stop(self): 
        # stop the MQTT client 
        self.mqtt_client.loop_stop() 
        # stop the state machine Driver 
        self.stm_driver.stop() 
        

# start logging  
debug_level = logging.DEBUG 
logger = logging.getLogger(__name__) 
logger.setLevel(debug_level) 
ch = logging.StreamHandler() 
ch.setLevel(debug_level) 
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s') 
ch.setFormatter(formatter) 
logger.addHandler(ch) 

# get number of scooters to spawn
number_of_scooters_to_spawn = sys.argv[1]

# initiate scooter manager
scooter_manager = ScooterManager(int(number_of_scooters_to_spawn)) 


