import paho.mqtt.client as mqtt 
import stmpy 
import logging 
import json 
import matplotlib.pyplot as plt 
 
MQTT_BROKER = 'mqtt20.iik.ntnu.no' 
MQTT_PORT = 1883

MQTT_TOPIC_POSITIONS = '10/scooter_positions' 
MQTT_TOPIC_SERVER_REQUESTS = '10/server_request'
MQTT_TOPIC_MANAGER = '10/manager'

STATUS_FREE = 'free'
STATUS_BOOKED = 'booked'


class ServerLogic: 

    def __init__(self, name, component): 
        self._logger = logging.getLogger(__name__) 
        self.name = name 
        self.component = component 
        # self.positional_data = positional_data
        self.single_booking_to_resend = 'empty'

        # server transitions
        t0 = {'source': 'initial', 'target': 'idle'}
        t1 = {'source': 'idle', 'target': 'await_position_data', 'trigger': 'get_positional_data', 'effect': 'request_positions'} 
        t2 = {'source': 'await_position_data', 'target': 'idle', 'trigger': 't0', 'effect': 'generate_heatmap'} 
        t3 = {'source': 'idle', 'target': 'final', 'trigger': 'abort', 'effect': 'say_goodbye'}
        t4 = {'source': 'idle', 'target':'await_booking_data', 'trigger': 'book_single', 'effect': 'get_single_booking_confirmation'}
        t5 = {'source': 'await_booking_data', 'target':'await_booking_data', 'trigger': 't1', 'effect': 'get_single_booking_confirmation'}
        t6 = {'source': 'await_booking_data', 'target':'idle', 'trigger': 'ack_booking', 'effect': 'timestamp_registered'}

        # entry actions and deferred event
        await_position_data = {'name': 'await_position_data', 'entry': 'start_timer("t0", "20000")', 'exit': 'stop_timer("t0")', 'book_single': 'defer'}
        await_booking_data = {'name': 'await_booking_data', 'entry': 'start_timer("t1", "20000")', 'exit': 'stop_timer("t1")', 'book_single': 'defer'}
                
        # adding stm to driver
        self.stm = stmpy.Machine(name=name, transitions = [t0, t1, t2, t3, t4, t5, t6 ], obj=self, states = [await_position_data, await_booking_data]) 
        self.component.stm_driver.add_machine(self.stm) 
    
    
    def timestamp_registered(self):
        self.single_booking_to_resend = 'empty'
    
    
    def get_single_booking_confirmation(self):
        self._logger.debug('Server requests scooters timestemp.')
        if self.single_booking_to_resend == 'empty':
            scooter_name = self.component.single_booking_queue.pop(0)
            message = {'msg': 'confirm_booking','scooter_name' : scooter_name}
            payload = json.dumps(message)
            self.single_booking_to_resend = payload
        self.component.mqtt_client.publish(MQTT_TOPIC_SERVER_REQUESTS, self.single_booking_to_resend) 
        
    def say_goodbye(self):
        self._logger.debug(f'{self.name} says : GOODBYE!') 
        self.component.mqtt_client.publish(MQTT_TOPIC_SERVER_REQUESTS, '''{"msg": "abort"}''') 
        
    def request_positions(self):
        self._logger.debug('Server requests coordinate data from scooters.')
        self.component.mqtt_client.publish(MQTT_TOPIC_SERVER_REQUESTS, '''{"msg": "give_coordinates"}''') 
        
    def generate_heatmap(self):
        x = []
        y = []
        for k, v in self.component.positional_data.items():
            x.append(v[0])
            y.append(v[1])
        self.component.positional_data.clear()
        print(self.component.positional_data)
        plt.xlim([0, 988])
        plt.ylim([0, 661])
        img = plt.imread('map.png')
        fig, ax = plt.subplots()
        plt.axis('off')
        ax.imshow(img)
        ax.plot(x, y, 'bo')
        plt.savefig('uimages/scooter_plot.png')
        

         
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
        
        
        
        # TODO    
        # redo if transitions with : https://falkr.github.io/stmpy/transitions.html     
        
        if command == 'coordinates':
            print(self.positional_data)
            # check which state server in 
            # if server is in 'await_position_data' state, then accept coordinates
            # if server is in any other state, ignore coordinates, since we are not collecting data at the moment, 
            # this is just a delayed response, we don't want to receive stale coordinates 
            if self.stm_driver._stms_by_id['my_server']._state == 'await_position_data':
                x = payload.get('x')
                y = payload.get('y')
                scooter_name = payload.get('scooter_name')
                self._logger.debug(f'Received coordinates from {scooter_name} : ({x}, {y})')
                self.positional_data[scooter_name] = (x, y)
            
        if command == 'get_positional_data':
            self.stm_driver.send('get_positional_data', 'my_server') 
                        
        if command == 'abort':
            self.stm_driver.send('abort', 'my_server') 
            
        if command == 'book_single':
            scooter_name = payload.get('scooter_name')
            # only book free scooters, otherwise #TODO notify user?
            if(self.scooter_stats[scooter_name][0] == STATUS_FREE):
                user_name = payload.get('user_name')
                self.scooter_stats[scooter_name] = (STATUS_BOOKED, user_name, None)
                self.single_booking_queue.append(scooter_name)
                self.stm_driver.send('book_single', 'my_server') 
            
        if command == 'book_multiple':
            print()
                        
        if command == 'ack_booking':
            # if status is booked, but timestamp is missing, add timestamp, otherwise ignore, it got lost in the ether
            scooter_name = payload.get('scooter_name')
            if(self.scooter_stats[scooter_name][0] == STATUS_BOOKED and self.scooter_stats[scooter_name][2] == None):
                timestamp = payload.get('timestamp')
                username = self.scooter_stats[scooter_name][1]
                self.scooter_stats[scooter_name] = (STATUS_BOOKED, username, timestamp)
                self.stm_driver.send('ack_booking', 'my_server') 
                
            
    def __init__(self, number_of_scooters): 
        self._logger = logging.getLogger(__name__) 
        print('logging under name {}.'.format(__name__)) 
        self._logger.info('Initializing MQTT client') 
        self.positional_data = {}
        self.scooter_stats = {}
        self.single_booking_queue = []
        for i in range(0, number_of_scooters):
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
        self.mqtt_client.subscribe(MQTT_TOPIC_POSITIONS)
        self.mqtt_client.subscribe(MQTT_TOPIC_MANAGER) 

        # start the internal loop to process MQTT messages 
        self.mqtt_client.loop_start() 

        # start the stmpy driver, without any state machines for now 
        self.stm_driver = stmpy.Driver() 
        self.stm_driver.start(keep_active=True) 
        self._logger.debug('Component initialization finished') 
        
        # initiate an instance of Server stm, call it "my_server"
        self._logger.debug('Initializing Server STM with name "my_server"') 
        ServerLogic("my_server", self)
        
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









