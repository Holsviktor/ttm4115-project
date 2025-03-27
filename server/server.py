import paho.mqtt.client as mqtt 
from threading import Thread 
import logging
from MQTT_TOPICS import *

 
print(MQTT_TOPIC_SCOOTER_DRIVE)

MQTT_BROKER = 'mqtt20.iik.ntnu.no' 
MQTT_PORT = 1883 

MQTT_TOPIC_SCOOTER = '10/scooter' 
MQTT_TOPIC_CHARGER = '10/charger'

class Server: 

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
            
    def __init__(self): 

        self._logger = logging.getLogger(__name__) 
        print('logging under name {}.'.format(__name__)) 
        self._logger.info('Initializing MQTT client') 

        # create a new MQTT client 
        self.mqtt_client = mqtt.Client() 
        self.mqtt_client.on_connect = self.on_connect 
        self.mqtt_client.on_message = self.on_message 
        self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT) 
        self.mqtt_client.subscribe(MQTT_TOPIC_SCOOTER) 
        self.mqtt_client.loop_start() 
        self._logger.debug('Connecting to MQTT broker {} at port {}'.format(MQTT_BROKER, MQTT_PORT)) 
        
    def stop(self): 
        # stop the MQTT client 
        self.mqtt_client.loop_stop() 
        # stop the state machine Driver 
        self.stm_driver.stop() 


if __name__ == "__main__":
    debug_level = logging.DEBUG 
    logger = logging.getLogger(__name__) 
    logger.setLevel(debug_level) 
    ch = logging.StreamHandler() 
    ch.setLevel(debug_level) 
    formatter = logging.Formatter('%(asctime)s - %(name)-12s - %(levelname)-8s - %(message)s') 
    ch.setFormatter(formatter) 
    logger.addHandler(ch) 

    cm = Server() 
