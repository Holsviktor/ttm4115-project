import paho.mqtt.client as mqtt 
import stmpy 
import logging 
import json 
 
MQTT_BROKER = 'mqtt20.iik.ntnu.no' 
MQTT_PORT = 1883 

MQTT_TOPIC_FROM_CHARGER_TO_SCOOTERS = '10/from_charger_to_scooters'
MQTT_TOPIC_FROM_SERVER_TO_CHARGER = '10/from_server_to_charger'
MQTT_TOPIC_FROM_CHARGER_TO_USER_APPS = '10/from_charger_to_user_apps'
MQTT_TOPIC_FROM_SCOOTERS_TO_CHARGER = '10/from_scooters_to_charger'
MQTT_TOPIC_FROM_USER_APPS_TO_CHARGER = '10/from_user_apps_to_charger'
MQTT_TOPIC_TO_SERVER = '10/to_server'


class ChargerLogic: 


    def __init__(self, name, component): 

        self._logger = logging.getLogger(__name__) 
        self.name = name 
        self.component = component 

        #charger state machine transitions
        t0 = {'source': 'initial', 'target': 'idle'}
        t1 = {'source': 'idle', 'target': 'would_you_like_to_charge', 'trigger': 'ask_for_discount', 'effect': 'send_message_to_scooter'} 
        t2 = {'source': 'would_you_like_to_charge', 'target': 'idle', 'trigger': 't0', 'effect': 'give_discount_2'} 
        t3 = {'source': 'would_you_like_to_charge', 'target': 'idle', 'trigger': 'yes_charge', 'effect': 'give_discount_5'} 
        t4 = {'source': 'idle', 'target': 'final', 'trigger':'abort', 'effect' : 'say_goodbye'}
        
        # entry actions
        would_you_like_to_charge = {'name': 'would_you_like_to_charge', 'entry': 'start_timer("t0", "10000")', 'exit': 'stop_timer("t0")', 'ask_for_discount': 'defer'}
        

        self.stm = stmpy.Machine(name=name, transitions = [t0, t1, t2, t3, t4], obj=self, states = [would_you_like_to_charge]) 
        self.component.stm_driver.add_machine(self.stm) 
        
    def say_goodbye(self):
        self._logger.debug(f'{self.name} says : GOODBYE!') 
                
    def send_message_to_scooter(self):
        # activate scooter charging response
        message = {'scooter_name' : self.component.scooter_name, 'msg': 'would_you_like_to_charge'}
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_CHARGER_TO_SCOOTERS, payload) 
        # ask user if they can place scooter in charge
        message = {'user_name' : self.component.user_name, 'msg': 'would_you_like_to_charge'}
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_CHARGER_TO_USER_APPS, payload) 
        
    def give_discount_2(self):
        message = {'scooter_name' : self.component.scooter_name, 'msg': '2'}
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_TO_SERVER, payload) 
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_CHARGER_TO_SCOOTERS, payload)
    
    def give_discount_5(self):
        message = {'scooter_name' : self.component.scooter_name, 'msg': '5'}
        payload = json.dumps(message)
        self.component.mqtt_client.publish(MQTT_TOPIC_TO_SERVER, payload) 
        self.component.mqtt_client.publish(MQTT_TOPIC_FROM_CHARGER_TO_SCOOTERS, payload)
                

class ChargerManager: 

    def on_connect(self, client, userdata, flags, rc): 
        self._logger.debug('MQTT connected to {}'.format(client)) 

    def on_message(self, client, userdata, msg): 
        try: 
            payload = json.loads(msg.payload.decode('utf-8')) 
        except Exception as err: 
            self._logger.error('Message sent to topic {} had no valid JSON. Message ignored. {}'.format(msg.topic, err)) 
            return 
        
        command = payload.get('msg') 
        
        self._logger.debug('CHARGER Incoming message to topic {} : "{}" '.format(msg.topic, command) ) 
        
        # do stuff depending on what command you receive

        if command == 'yes_charge':
            self.scooter_name = payload.get('scooter_name')
            self.stm_driver.send('yes_charge', self.name) 
            
        if command == 'ask_for_discount':
            self.scooter_name = payload.get('scooter_name')
            self.user_name = payload.get('user_name')
            self.stm_driver.send('ask_for_discount', self.name) 
        
        if command == 'abort':
            self.stm_driver.send('abort', self.name) 
            
    def __init__(self): 

        self._logger = logging.getLogger(__name__) 
        print('logging under name {}.'.format(__name__)) 
        self._logger.info('Initializing MQTT client') 

        # create a new MQTT client 
        self.mqtt_client = mqtt.Client() 
        self.name = 'central_charging_station'
        self.user_name = 'empty'
        self.scooter_name = 'empty'

        # callback methods 
        self.mqtt_client.on_connect = self.on_connect 
        self.mqtt_client.on_message = self.on_message 

        # Connect to the broker 
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT)) 
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT) 

        # subscribe to proper topic(s) of your choic 
        self.mqtt_client.subscribe(MQTT_TOPIC_FROM_SCOOTERS_TO_CHARGER) 
        self.mqtt_client.subscribe(MQTT_TOPIC_FROM_SERVER_TO_CHARGER)
        self.mqtt_client.subscribe(MQTT_TOPIC_FROM_USER_APPS_TO_CHARGER)

        # start the internal loop to process MQTT messages 
        self.mqtt_client.loop_start() 

        # start the stmpy driver, without any state machines for now 
        self.stm_driver = stmpy.Driver() 
        self.stm_driver.start(keep_active=True) 
        self._logger.debug('Component initialization finished') 
        
        # initiate an instance of Charger stm, call it 'charger1'
        self._logger.debug(f'Initializing Charger STM with name {self.name}') 
        ChargerLogic(self.name, self)
        
        
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