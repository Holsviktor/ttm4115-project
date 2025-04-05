# MQTT server config
MQTT_BROKER = 'mqtt20.iik.ntnu.no' 
MQTT_PORT = 1883 

# Generel MQTT topics
MQTT_TOPIC_SCOOTER = '10/scooter' 
MQTT_TOPIC_CHARGER = '10/charger'

#
# Scooter drive MQTT topics
#

# 1Hz
TOPIC_SCOOTER_STATUS = "10/scooter/status"
TOPIC_CHARGER_STATUS = "10/charger/status"

#msg_status = {"name": , "latitude": , "longitude": , "in_use": , "state"}

# Charger publish topics
TOPIC_MOVEMNT = "10/charger/movement"

#
# Charger Request
#
#from charger
TOPIC_REQUEST_CHARGE = "10/charger/request_charge" # msg filed
#from scooter
TOPIC_RESPONSE_CHARGE = "10/scooter/response_charge" # msg filed: yes/no

TOPIC_END_CHARGE = "10/charger/end_charge"

#
# Scooter Request
# 

TOPIC_REQUEST_UNLOCK = "10/scooter/unlock/request"
TOPIC_RESPINSE_UNLOCK = "10/scooter/unlock/response"  # 1 if success

TOPIC_REQUEST_LOCK = "10/scooter/lock/request"
TOPIC_RESPONSE_LOCK  = "10/scooter/lock/responset"

#
# Server Topics
#

TOPIC_DISCOUNT = "10/server/discount" # msg filed: valuse of discount given (x%)
