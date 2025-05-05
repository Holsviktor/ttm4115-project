import paho.mqtt.client as mqtt 
import stmpy 
import logging 
import json 
import matplotlib.pyplot as plt 
import time
 
MQTT_BROKER = 'mqtt20.iik.ntnu.no' 
MQTT_PORT = 1883

MQTT_TOPIC_SCOOTER_POSITIONS = '10/scooter_positions'
MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS = '10/server_request'
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
        self.single_cancel_data = 'empty'

        # server transitions
        t0 = {'source': 'initial', 'target': 'idle'}
        t1 = {'source': 'idle', 'target': 'await_position_data', 'trigger': 'get_positional_data', 'effect': 'request_positions'} 
        t2 = {'source': 'await_position_data', 'target': 'idle', 'trigger': 't0', 'effect': 'generate_heatmap'} 
        t3 = {'source': 'idle', 'target': 'final', 'trigger': 'abort', 'effect': 'say_goodbye'}
        t4 = {'source': 'idle', 'target':'await_booking_data', 'trigger': 'book_single', 'effect': 'get_single_booking_confirmation'}
        t5 = {'source': 'await_booking_data', 'target':'await_booking_data', 'trigger': 't1', 'effect': 'get_single_booking_confirmation'}
        t6 = {'source': 'await_booking_data', 'target':'idle', 'trigger': 'ack_booking', 'effect': 'timestamp_registered'}
        t7 = {'source': 'idle', 'target': 'idle', 'trigger': 'scooterlist_request', 'effect': 'send_info_to_user'}
        t8 = {'source': 'idle', 'target': 'await_discount_information', 'trigger': 'end_book_single', 'effect': 'end_single_booking_confirmation'}
        
        t9 = {'source': 'await_discount_information', 'target': 'await_discount_information', 'trigger': 'get_final_coordinates', 'effect':'request_final_coordinates'}
        t10 = {'source': 'await_discount_information', 'target': 'await_discount_information', 'trigger': 'my_final_coordinates', 'effect': 'request_discount_info'}
        t11 = {'source': 'await_discount_information', 'target': 'idle', 'trigger': 'finalize', 'effect': 'finalize_end_single_booking_confirmation'}
        t12 = {'source': 'await_discount_information', 'target': 'idle', 'trigger': 'discount', 'effect': 'finalize_end_single_booking_confirmation'}

        # entry actions and deferred event
        await_position_data = {'name': 'await_position_data', 'entry': 'start_timer("t0", "10000")', 'exit': 'stop_timer("t0")', 'book_single': 'defer', 'end_book_single' : 'defer'}
        await_booking_data = {'name': 'await_booking_data', 'entry': 'start_timer("t1", "10000")', 'exit': 'stop_timer("t1")', 'book_single': 'defer', 'end_book_single' : 'defer'}
        await_discount_information = {'name': 'await_discount_information', 'book_single': 'defer', 'end_book_single' : 'defer'}
                
        # adding stm to driver
        self.stm = stmpy.Machine(name=name, transitions = [t0, t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12 ], obj=self, states = [await_position_data, await_booking_data, await_discount_information]) 
        self.component.stm_driver.add_machine(self.stm) 
     
    
    def end_single_booking_confirmation(self):
        self.single_cancel_data = self.component.single_cancel_queue.pop(0)
        self.component.stm_driver.send('get_final_coordinates', self.name)
        
    def request_final_coordinates(self):
        self._logger.debug(f'{self.name} requests final coordinates.')
        message = {'msg': 'give_final_coordinates', 'scooter_name' : self.single_cancel_data[0]}
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS, payload) 
        
        #self.single_cancel_queue.append([scooter_name, user_name, booking_started_at, booking_ended_at, discount])  
    def request_discount_info(self):
        self._logger.debug(f'{self.name} evaluates discount info.')
        # user can have discount, find out how much
        if(abs(self.component.charger_x - self.component.final_coordinates[self.single_cancel_data[0]][0]) <= 5 
           and 
           abs(self.component.charger_y - self.component.final_coordinates[self.single_cancel_data[0]][1]) <= 5):
            message = {'msg': 'ask_for_discount', 'scooter_name' : self.single_cancel_data[0], 'user_name': self.single_cancel_data[1]}
            payload = json.dumps(message)
            self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_CHARGER, payload) 
            # remove stale coordinates
            self.component.final_coordinates.pop(self.single_cancel_data[0])
        # user cannot have discount, finalize end of single booking  
        else:
            # the user is not near the charging station, no discount available
            self.component.discount[self.single_cancel_data[0]] = 0
            # remove stale coordinates
            self.component.final_coordinates.pop(self.single_cancel_data[0])
            self.component.stm_driver.send('finalize', self.name)
        
    def finalize_end_single_booking_confirmation(self):  
        # log previous bookings in a "database"
        self._logger.debug(f'{self.name} tries to finalize end_single_booking.')
        # user can have discount, find out how much
        self._logger.debug(f'-------------->{self.single_cancel_data[0]} : {self.component.discount}') 
        self._logger.debug(f'-------------->{self.single_cancel_data}')
        self.component.past_bookings[self.component.index] = (self.single_cancel_data[1], self.single_cancel_data[0], self.single_cancel_data[2], self.single_cancel_data[3], self.component.discount[self.single_cancel_data[0]])
        self.component.index += 1
        message = {'user_name' : self.single_cancel_data[1], 'msg': 'ack_end_book_single'}
        reply = json.dumps(message)        
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS, reply)
        # reset server internal scooter stats
        self.component.scooter_stats[self.single_cancel_data[0]] = (STATUS_FREE, None, None)
        message = {'msg': 'stop_booking','scooter_name' : self.single_cancel_data[0]}
        # send trip cancellation to scooter
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS, payload)

        # remove inner stale data       
        self.component.discount.pop(self.single_cancel_data[0])
        self.single_cancel_data = 'empty'
        
    def send_info_to_user(self):
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS, self.component.payload) 
        self.component.payload = 'empty'
        
    def timestamp_registered(self):
        self.single_booking_to_resend = 'empty'
    
    def get_single_booking_confirmation(self):
        self._logger.debug(f'{self.name} requests scooters timestamp.')
        if self.single_booking_to_resend == 'empty':
            scooter_name = self.component.single_booking_queue.pop(0)
            message = {'msg': 'confirm_booking','scooter_name' : scooter_name}
            payload = json.dumps(message)
            self.single_booking_to_resend = payload
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS, self.single_booking_to_resend) 
        
    def say_goodbye(self):
        self._logger.debug(f'{self.name} says : GOODBYE!') 
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_SCOOTERS, '''{"msg": "abort"}''') 
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_CHARGER, '''{"msg": "abort"}''') 
        
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
                # save current canceling info in cancel queue
                booking_ended_at = time.time()
                discount = None
                self.single_cancel_queue.append([scooter_name, user_name, self.scooter_stats[scooter_name][2], booking_ended_at, discount])
                # THEN, send it all to STM and finish all in there....
                self.stm_driver.send('end_book_single', self.name)
            else:
                # scooter is already booked, or username didn't match
                message = {'user_name' : user_name, 'msg': 'cancel_denied', 'scooter_name': scooter_name}
                reply = json.dumps(message)        
                self.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS, reply)
                    
        #TODO discount

        #TODO cancel  multiple ride
        #{'msg': 'end_book_multiple', 'user_name' : username, 'scooter_name': scooter_name}
        if command == 'end_book_multiple':
            scooter_names = payload.get('scooter_names')
            user_name = payload.get('user_name')
            already_unavailable_scooters = []
            for scooter_name in scooter_names:
                if(self.scooter_stats[scooter_name][0] != STATUS_BOOKED):
                    already_unavailable_scooters.append(scooter_name)
                    print(f'{scooter_name} is ALREADY available!')
            if(len(already_unavailable_scooters) == 0):
                for scooter_name in scooter_names:
                    if(self.scooter_stats[scooter_name][0] == STATUS_BOOKED and self.scooter_stats[scooter_name][1] == user_name):
                        # log previous bookings in a "database"
                        discount = None
                        booking_ended_at = time.time()
                        self.past_bookings[self.index] = (user_name, scooter_name, self.scooter_stats[scooter_name][2], booking_ended_at, discount)
                        self.index += 1
                        message = {'user_name' : user_name, 'msg': 'ack_end_book_single'}
                        reply = json.dumps(message)        
                        self.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS, reply)
                        message = {'msg': 'stop_booking','scooter_name' : scooter_name}
                        payload = json.dumps(message)  
                        self.single_cancel_queue.append(payload)
                        self.stm_driver.send('end_book_single', self.name)
                        # reset current stats data for this scooter
                        self.scooter_stats[scooter_name] = (STATUS_FREE, None, None)
                        
                    else:
                        # either username didn't match or scooter is already free
                        message = {'user_name' : user_name, 'msg': 'cancel_denied', 'scooter_name': scooter_name}
                        reply = json.dumps(message)        
                        self.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS, reply)   
            else:
                # some scooters are already free
                message = {'user_name' : user_name, 'msg': 'cancel_denied', 'scooter_names': already_unavailable_scooters}
                reply = json.dumps(message)        
                self.mqtt_client.publish(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS, reply)
                  
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
                
        if command == 'my_final_coordinates':
            self.final_coordinates[payload.get('scooter_name')] = (payload.get('x'), payload.get('y'))
            self.stm_driver.send('my_final_coordinates', self.name) 
            
        if command == '2' or command == '5':
            self.discount[payload.get('scooter_name')] = int(command)
            self.stm_driver.send('discount', self.name) 
            
            
    def __init__(self, number_of_scooters): 
        # initializing server MQTT client and server stm logic
        self._logger = logging.getLogger(__name__) 
        print('logging under name {}.'.format(__name__)) 
        self._logger.info('Initializing MQTT client for server stm') 
        # grid coordinates info
        self.map_dim_x = 988
        self.map_dim_y = 661
        self.charger_x = 494
        self.charger_y = 330
        # server name
        self.name = 'central_server'
        # 
        self.positional_data = {}
        # 'database' dictionary 
        self.past_bookings = {}
        self.past_bookings[0] = ('-', '-', '-', '-', '-')
        self.index = 1
        # scooter stats overview dictionary
        self.scooter_stats = {}
        # booking info queue
        self.single_booking_queue = []
        # cancel info queue
        self.single_cancel_queue = []
        # dictionary to pla
        self.final_coordinates = {}
        self.payload = 'empty'
        self.discount = {}
        # initialize scooter stats for each scooter, overview is internal
        # the server keeps track of changing stats based on received commands
        for i in range(0, number_of_scooters):
            # each scooter can have the following data stored at the server: 
            # status (free/booked), username of the booker, timestamps of when scooter was booked 
            self.scooter_stats[f'scooter{i}'] = (STATUS_FREE, None, None)
            
            
        # REMOVE ________________________  
            if i == 8:
                break
            
        self.scooter_stats['test_discount'] = (STATUS_FREE, None, None)   
        
        
        #_______________________________

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