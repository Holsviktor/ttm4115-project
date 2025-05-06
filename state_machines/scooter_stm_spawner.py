from sense_hat import SenseHat
from threading import Thread 
import json
import logging 
import paho.mqtt.client as mqtt 
import random
import sense_hat_definitions
import stmpy 
import sys
import time



MQTT_BROKER = 'mqtt20.iik.ntnu.no' 
MQTT_PORT = 1883 
MQTT_TOPIC_SCOOTER_POSITIONS = '10/scooter_positions' 
MQTT_TOPIC_SCOOTER_STATUS = '10/scooter_status'
MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS = '10/server_request'
MQTT_TOPIC_TO_SERVER = '10/to_server'
MQTT_TOPIC_FROM_SCOOTERS_TO_CHARGER = '10/from_scooters_to_charger'
MQTT_TOPIC_FROM_CHARGER_TO_SCOOTERS = '10/from_charger_to_scooters'

class ScooterLogic: 

    def __init__(self, name, component, x, y): 

        self._logger = logging.getLogger(__name__) 
        self.name = name 
        self.component = component 
        self.sense = SenseHat()
        self.sense.clear()
        # 'GPS coordinates are internal'
        self.x = x 
        self.y = y
        self.ts = 'empty'
                
        self.enable_thread_Event_1Hz = True
        self.enable_thread_handle_joystick_input = True
        self.enable_thread_charge_response = False
        
        # scooter state machine transitions
        
        # initial transition
        t0 = {'source': 'initial', 'target': 'is_free'}
        
        # heatmap related transition
        t1 = {'source': 'is_free', 'target': 'is_free', 'trigger': 'give_coordinates', 'effect': 'send_coordinates'} 
        
        # shutdown related transitions
        t2 = {'source': 'is_free', 'target': 'final', 'trigger': 'abort', 'effect': 'say_goodbye'}
        t3 = {'source': 'in_use', 'target': 'final', 'trigger': 'abort', 'effect': 'say_goodbye'}
        
        # booking related transitions
        t4 = {'source': 'is_free', 'target': 'in_use', 'trigger': 'confirm_booking', 'effect' : 'unlock_animation; book_this'}
        t5 = {'source': 'in_use', 'target': 'in_use', 'trigger': 'confirm_booking', 'effect' : 'book_this'}
        
        # canceling related transition
        t6 = {'source': 'in_use', 'target': 'is_free', 'trigger': 'stop_booking', 'effect' : 'end_trip; lock_animation'}
        
        # discount related transition
        t7 = {'source': 'in_use', 'target': 'in_use', 'trigger': 'give_final_coordinates', 'effect': 'send_final_coordinates'}
        t8 = {'source': 'in_use', 'target': 'respond_to_charge_request', 'trigger': 'would_you_like_to_charge'} 
        t9 = {'source': 'respond_to_charge_request', 'target': 'in_use', 'trigger': '5', 'effect': 'five_animation'}
        t10 = {'source': 'respond_to_charge_request', 'target': 'in_use', 'trigger': '2', 'effect': 'two_animation'}
    
        
        # skip sending coordinates when scooter is booked, aka in_use 
        in_use = {'name': 'in_use', 'give_coordinates' : ''} 
       
        respond_to_charge_request = {'name': 'respond_to_charge_request', 'entry': 'contemplate_charging'}
        
        
        self.stm = stmpy.Machine(name=name, transitions = [t0, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10], obj=self, states = [in_use, respond_to_charge_request]) 
        self.component.stm_driver.add_machine(self.stm)
        
        # Threads used to avoid blocking main function
        self.thread_1Hz = Thread(target=self.Event_1Hz)
        self.thread_1Hz.start()

        self.thread_handle_joystick = Thread(target=self._handle_joystick_input)
        self.thread_handle_joystick.start()
        
        self.thread_handle_charge_response = Thread(target=self.handle_charge_response)
        self.thread_handle_charge_response.start()
        
    def contemplate_charging(self):
        self.sense.set_pixels(sense_hat_definitions.question_mark_pixels)
        
        
    # send final scooter position to server when ending trip
    def send_final_coordinates(self):
        message = {'msg': 'my_final_coordinates','scooter_name' : self.name, 'x': self.x, 'y': self.y}
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_TO_SERVER, payload) 
                    
    # animation of scooter getting 5% discount on sense hat
    def five_animation(self):
        self.sense.set_pixels(sense_hat_definitions.five_digit_pixels)
        time.sleep(2)
        self.sense.clear()
    
    # animation of scooter getting 2% discount on sense hat
    def two_animation(self):
        self.sense.set_pixels(sense_hat_definitions.two_digit_pixels)
        time.sleep(2)
        self.sense.clear()
               
    # animation of scooter locking on sense hat
    def lock_animation(self):
        self.ts = 'empty'
        self._logger.debug(f'{self.name} is LOCKED.')
        sense_hat_definitions.animate_locking(self.sense)
        self.sense.clear()
        
    # animation of scooter unlocking on sense hat
    def unlock_animation(self):
        self._logger.debug(f'{self.name} is UNLOCKED.')
        sense_hat_definitions.animate_unlocking(self.sense)
        self.sense.clear()
    
    # scooter ack to server that it is no longer booked
    def end_trip(self):
        if self.ts == 'empty':
            ts = time.time()
            self.ts = ts
        message = {'msg': 'ack_booking_finished','scooter_name' : self.name, 'timestamp': self.ts}
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_TO_SERVER, payload) 
    
    # scooter sends to server its coordinates   
    def send_coordinates(self):
            message = {'msg': 'coordinates','scooter_name' : self.name, 'x': self.x, 'y': self.y, 'scooter_state': self.component.stm_driver._stms_by_id[self.name]._state}
            payload = json.dumps(message)
            self.component.mqtt_client.publish(MQTT_TOPIC_SCOOTER_POSITIONS, payload) 
    
     # scooter ack to server that it is now booked
    def book_this(self):
        ts = time.time()
        message = {'msg': 'ack_booking','scooter_name' : self.name, 'timestamp': ts}
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_TO_SERVER, payload) 
        
    def say_goodbye(self):
        self.enable_thread_Event_1Hz = False
        self.enable_thread_handle_joystick_input = False
        self.enable_thread_charge_response = False
        self.thread_1Hz.join()
        self.thread_handle_joystick.join()
        self.thread_handle_charge_response.join()
        self._logger.debug(f'{self.name} says : GOODBYE!') 
        
    # sense hat functionality
    
    def handle_charge_response(self):  
        self.enable_thread_handle_joystick_input = False
        self.enable_thread_charge_response = True 
        while self.enable_thread_charge_response:
            for event in self.sense.stick.get_events():
                self._logger.debug(f'EVENT: ----> {event}')
                if(event.direction == ('up' or 'down' or 'right' or 'left')):
                    answer = True
                    # simulate setting scooter to charge
                    sense_hat_definitions._display_arrow('stop', self.sense)
                    msg = {'msg': 'yes_charge', 'scooter_name': self.name}
                    self._logger.debug('SCOOTER: MOTION REGISTERED.')
                    self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SCOOTERS_TO_CHARGER, payload=json.dumps(msg)) 
                    self.enable_thread_charge_response = False    
                    self.enable_thread_handle_joystick_input = True              
                    self.sense.clear()
        

    def Event_1Hz(self):
        while self.enable_thread_Event_1Hz:
            self.status = {'name': self.name, 'x': self.x, 'y': self.y, 'state' : self.component.stm_driver._stms_by_id[self.name]._state}
            msg = self.status
            time.sleep(1)
            self.component.mqtt_client.publish(MQTT_TOPIC_SCOOTER_STATUS, payload=json.dumps(msg))
        
    def _handle_joystick_input(self):
        while self.enable_thread_handle_joystick_input:
            if self.component.stm_driver._stms_by_id[self.name]._state != ('in_use'):
                time.sleep(0.1)
            else:
                for event in self.sense.stick.get_events():
                    self._logger.debug(f'EVENT: ----> {event}')
                    # x and y are adjusted to contain scooters in the grid
                    if event.action == 'pressed':
                        if event.direction == 'up':
                            sense_hat_definitions._display_arrow('up', self.sense)
                            self.x += 1
                            if self.x > 988:
                                self.x = 988
                        elif event.direction == 'down':
                            sense_hat_definitions._display_arrow('down', self.sense)
                            self.x -= 1
                            if self.x < 0:
                                self.x = 0
                        elif event.direction == 'left':
                            sense_hat_definitions._display_arrow('left', self.sense)
                            self.y -=1
                            if self.y < 0:
                                self.y = 0
                        elif event.direction == 'right':
                            sense_hat_definitions._display_arrow('right', self.sense)
                            self.y += 1
                            if self.y > 661:
                                self.y = 661
                        else:
                            sense_hat_definitions._display_arrow('stop', self.sense)
                    self.sense.clear()
                            
class ScooterManager: 

    def on_connect(self, client, userdata, flags, rc): 
        self._logger.debug('Scooter MQTT connected to {}'.format(client)) 

    def on_message(self, client, userdata, msg): 
        
        try: 
            payload = json.loads(msg.payload.decode('utf-8')) 
        except Exception as err: 
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err)) 
            return 
        
        command = payload.get('msg') 
        
        self._logger.debug('SCOOTER Incoming message to topic {} : "{}" '.format(msg.topic, command) ) 
          
        # do stuff depending on what command you receive
        
        if command == 'give_coordinates':
            for stm_id in self.stm_driver._stms_by_id:
                self.stm_driver.send('give_coordinates', stm_id) 
                
        if command == 'abort':
            for stm_id in self.stm_driver._stms_by_id: 
                self.stm_driver.send('abort', stm_id)
            
        if command == 'confirm_booking':
            self.stm_driver.send('confirm_booking', payload.get('scooter_name'))
            
        if command == 'stop_booking':
            self.stm_driver.send('stop_booking', payload.get('scooter_name'))
            
        if command == 'stop_booking_confirmed':
            self.stm_driver.send('stop_booking_confirmed', payload.get('scooter_name'))
            
        if command == 'give_final_coordinates':
            self.stm_driver.send('give_final_coordinates', payload.get('scooter_name'))
            
        if command == 'would_you_like_to_charge':
            self.stm_driver.send('would_you_like_to_charge', payload.get('scooter_name'))
            
        if command == '5':
            self.stm_driver.send('5', payload.get('scooter_name'))
        
        if command == '2':
            self.stm_driver.send('2', payload.get('scooter_name'))

            
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

        # subscribe to proper topic(s) of your choice
        self.mqtt_client.subscribe(MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS) 
        self.mqtt_client.subscribe(MQTT_TOPIC_FROM_CHARGER_TO_SCOOTERS) 
        
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
            
        #REMOVE:#____________________
            if i == 8:
                break
            
            
        self.scooters.append('test_discount')  
        self._logger.debug(f'Initializing Scooter STM with name "test_discount"') 
        ScooterLogic(f'test_discount', self, x = 510, y = 360)
        #____________________
        
        
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



