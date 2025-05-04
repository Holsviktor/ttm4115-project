import paho.mqtt.client as mqtt 
import stmpy 
import logging 
import json 
import matplotlib.pyplot as plt 
import time
 
MQTT_BROKER = 'mqtt20.iik.ntnu.no' 
MQTT_PORT = 1883

MQTT_TOPIC_SCOOTER_POSITIONS = '10/scooter_positions'
MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS = '10/from_server_to_scooters'
MQTT_TOPIC_FROM_SERVER_TO_USER_APPS = '10/from_server_to_user_apps'
MQTT_TOPIC_FROM_SERVER_TO_CHARGER = '10/from_server_to_charger'
MQTT_TOPIC_TO_SERVER = '10/to_server'

STATUS_FREE = 'free'
STATUS_BOOKED = 'booked'


class ServerLogic: 

    def __init__(self, name, component): 
        self._logger = logging.getLogger(__name__) 
        self.name = name 
        self.component = component 
        self.single_booking_to_resend = 'empty'

        # server transitions
        t0 = {'source': 'initial', 'target': 'idle'}
        t1 = {'source': 'idle', 'target': 'await_position_data', 'trigger': 'get_positional_data', 'effect': 'request_positions'} 
        t2 = {'source': 'await_position_data', 'target': 'idle', 'trigger': 't0', 'effect': 'generate_heatmap'} 
        t3 = {'source': 'idle', 'target': 'final', 'trigger': 'abort', 'effect': 'say_goodbye'}
        t4 = {'source': 'idle', 'target':'await_booking_data', 'trigger': 'book_single', 'effect': 'get_single_booking_confirmation'}
        t5 = {'source': 'await_booking_data', 'target':'await_booking_data', 'trigger': 't1', 'effect': 'get_single_booking_confirmation'}
        t6 = {'source': 'await_booking_data', 'target':'idle', 'trigger': 'ack_booking', 'effect': 'timestamp_registered'}
        t7 = {'source': 'idle', 'target': 'idle', 'trigger': 'scooterlist_request', 'effect': 'send_info_to_user'}
        t8 = {'source': 'idle', 'target': 'idle', 'trigger': 'end_book_single', 'effect': 'end_single_booking_confirmation'}
        
        

        # entry actions and deferred event
        await_position_data = {'name': 'await_position_data', 'entry': 'start_timer("t0", "10000")', 'exit': 'stop_timer("t0")', 'book_single': 'defer'}
        await_booking_data = {'name': 'await_booking_data', 'entry': 'start_timer("t1", "10000")', 'exit': 'stop_timer("t1")', 'book_single': 'defer'}
                
        # adding stm to driver
        self.stm = stmpy.Machine(name=name, transitions = [t0, t1, t2, t3, t4, t5, t6, t7, t8 ], obj=self, states = [await_position_data, await_booking_data]) 
        self.component.stm_driver.add_machine(self.stm) 
        
    def end_single_booking_confirmation(self):
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS, self.component.payload)
        self.component.payload = 'empty'
        
        
    def send_info_to_user(self):
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS, self.component.payload) 
        self.component.payload = 'empty'
        
        
    def timestamp_registered(self):
        self.single_booking_to_resend = 'empty'
    
    
    def get_single_booking_confirmation(self):
        self._logger.debug(f'Server requests scooters timestamp.')
        if self.single_booking_to_resend == 'empty':
            scooter_name = self.component.single_booking_queue.pop(0)
            message = {'msg': 'confirm_booking','scooter_name' : scooter_name}
            payload = json.dumps(message)
            self.single_booking_to_resend = payload
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS, self.single_booking_to_resend) 
        
    def say_goodbye(self):
        self._logger.debug(f'{self.name} says : GOODBYE!') 
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS, '''{"msg": "abort"}''') 
        
    def request_positions(self):
        self._logger.debug('Server requests coordinate data from scooters.')
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS, '''{"msg": "give_coordinates"}''') 
        
    def generate_heatmap(self):
        x = []
        y = []
        for k, v in self.component.positional_data.items():
            x.append(v[0])
            y.append(v[1])
        self.component.positional_data.clear()
        plt.xlim([0, self.component.map_dim_x])
        plt.ylim([0, self.component.map_dim_x])
        img = plt.imread('map.png')
        _, ax = plt.subplots()
        plt.axis('off')
        ax.imshow(img)
        ax.plot(x, y, 'bo', label = 'scooters')
        ax.plot(self.component.charger_x, self.component.charger_y, 'o', color = 'orange', label = 'charging station')
        ax.legend(loc='upper right')
        plt.savefig('images/scooter_plot.png')
        
      
class ServerManager: 

    def on_connect(self, client, userdata, flags, rc): 
        self._logger.debug('Server MQTT connected to {}'.format(client)) 

    def on_message(self, client, userdata, msg): 
        try: 
            payload = json.loads(msg.payload.decode("utf-8")) 
        except Exception as err: 
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err)) 
            return 
        
        command = payload.get('msg') 
        
        self._logger.debug('SERVER: Incoming message to topic {} : "{}" '.format(msg.topic, command)) 
        
        # do stuff depending on what command you receive   
           
        if command == 'coordinates':
            # check which state server in 
            # if server is in 'await_position_data' state, then accept coordinates
            # if server is in any other state, ignore coordinates, since we are not collecting data at the moment, 
            # this is a delayed response, we don't want to receive stale coordinates 
            if self.stm_driver._stms_by_id[self.name]._state == 'await_position_data':
                x = payload.get('x')
                y = payload.get('y')
                scooter_name = payload.get('scooter_name')
                self._logger.debug(f'Received coordinates from {scooter_name} : ({x}, {y})')
                self.positional_data[scooter_name] = (x, y)
            
        if command == 'get_positional_data':
            self.stm_driver.send('get_positional_data', self.name) 
                        
        if command == 'abort':
            self.stm_driver.send('abort', self.name) 
            
        if command == 'book_single':
            scooter_name = payload.get('scooter_name')
            user_name = payload.get('user_name')
            # assume usernames are unique
            # only book free scooters, otherwise notify user
            if(self.scooter_stats[scooter_name][0] == STATUS_FREE):
                self.scooter_stats[scooter_name] = (STATUS_BOOKED, user_name, None)
                self.single_booking_queue.append(scooter_name)
                self.stm_driver.send('book_single', self.name)
            else:
                message = {'user_name': user_name,'msg':'single_not_available', 'scooter_name' : scooter_name}
                reply = json.dumps(message)
                self.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS, reply) 
                
        if command == 'scooterlist_request':
            user_name = payload.get('user_name') 
            message = {'user_name' : user_name, 'msg': 'scooter_information', 'x_dim' : self.map_dim_x, 'y_dim': self.map_dim_y, 'charger_x' : self.charger_x, 'charger_y' : self.charger_y,'scooter_names' : list(self.scooter_stats.keys())}
            self.payload = json.dumps(message)        
            self.stm_driver.send('scooterlist_request', self.name)
            
        if command == 'end_book_single':
            scooter_name = payload.get('scooter_name')
            user_name = payload.get('user_name')
            if(self.scooter_stats[scooter_name][0] == STATUS_BOOKED and self.scooter_stats[scooter_name][1] == user_name):
                # TODO check if scooter near charging station
                
                discount = None
                booking_ended_at = time.time()
                # log previous bookings in a "database"
                self.past_bookings[self.index] = (user_name, scooter_name, self.scooter_stats[scooter_name][2], booking_ended_at, discount)
                self.index += 1
                message = {'user_name' : user_name, 'msg': 'ack_end_book_single'}
                reply = json.dumps(message)        
                self.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS, reply)
                message = {'msg': 'stop_booking','scooter_name' : scooter_name}
                self.payload = json.dumps(message)  
                self.stm_driver.send('end_book_single', self.name)
            else:
                message = {'user_name' : user_name, 'msg': 'cancel_denied', 'scooter_name': scooter_name}
                reply = json.dumps(message)        
                self.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS, reply)
            
                
        #TODO cancel  multiple ride
        
        #TODO discount
                  
        if command == 'book_multiple':
            scooter_names = payload.get('scooter_names')
            user_name = payload.get('user_name')
            unavailable_scooters = []
            for scooter_name in scooter_names:
                if(self.scooter_stats[scooter_name][0] != STATUS_FREE):
                    unavailable_scooters.append(scooter_name)
                    print(f'{scooter_name} is NOT available!')
            if(len(unavailable_scooters) == 0):
                for scooter_name in scooter_names:
                    self.scooter_stats[scooter_name] = (STATUS_BOOKED, user_name, None)
                    self.single_booking_queue.append(scooter_name)
                    self.stm_driver.send('book_single', self.name)
            else:
                message = {'user_name': user_name, 'msg' : 'multiple_not_available', 'scooter_names' : unavailable_scooters}
                payload = json.dumps(message)
                self.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS, payload) 
                        
        if command == 'ack_booking':
            # if status is booked, but timestamp is missing, add timestamp, otherwise ignore,
            # because the first received timestamp indicates the start of booking
            scooter_name = payload.get('scooter_name')
            if(self.scooter_stats[scooter_name][0] == STATUS_BOOKED and self.scooter_stats[scooter_name][2] == None):
                timestamp = payload.get('timestamp')
                username = self.scooter_stats[scooter_name][1]
                self.scooter_stats[scooter_name] = (STATUS_BOOKED, username, timestamp)
                self.stm_driver.send('ack_booking', self.name) 
                
            
    def __init__(self, number_of_scooters): 
        # initializing server MQTT client and server stm logic
        self.map_dim_x = 988
        self.map_dim_y = 661
        self.charger_x = 494
        self.charger_y = 330
        self.name = 'central_server'
        self._logger = logging.getLogger(__name__) 
        print('logging under name {}.'.format(__name__)) 
        self._logger.info('Initializing MQTT client') 
        self.past_bookings = {}
        
        self.positional_data = {}
        self.scooter_stats = {}
        self.past_bookings[0] = ('-', '-', '-', '-', '-')
        self.index = 1
        self.single_booking_queue = []
        self.payload = 'empty'
        for i in range(0, number_of_scooters):
            # each scooter can have the following data stored at the server: 
            # status (free/booked), username of the booker, timestamps of when scooter was booked 
            self.scooter_stats[f'scooter{i}'] = (STATUS_FREE, None, None)

        # create a new MQTT client 
        self.mqtt_client = mqtt.Client() 

        # callback methods 
        self.mqtt_client.on_connect = self.on_connect 
        self.mqtt_client.on_message = self.on_message 

        # connect to the broker 
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT)) 
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT) 

        # subscribe to proper topic(s) of your choice
        self.mqtt_client.subscribe(MQTT_TOPIC_SCOOTER_POSITIONS)
        self.mqtt_client.subscribe(MQTT_TOPIC_TO_SERVER) 

        # start the internal loop to process MQTT messages 
        self.mqtt_client.loop_start() 

        # start the stmpy driver, without any state machines for now 
        self.stm_driver = stmpy.Driver() 
        self.stm_driver.start(keep_active=True) 
        self._logger.debug('Component initialization finished') 
        
        # initiate an instance of Server stm, call it "my_server"
        self._logger.debug(f'Initializing Server STM with name "{self.name}"') 
        ServerLogic(self.name, self)
        
    def stop(self): 
        # stop the MQTT client 
        self.mqtt_client.loop_stop() 
        # stop the state machine Driver 
        self.stm_driver.stop() 
        
def create_server_manager(number_of_scooters):
    return ServerManager(number_of_scooters)

debug_level = logging.DEBUG 
logger = logging.getLogger(__name__) 
logger.setLevel(debug_level) 
ch = logging.StreamHandler() 
ch.setLevel(debug_level) 
formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s') 
ch.setFormatter(formatter) 
logger.addHandler(ch) 






