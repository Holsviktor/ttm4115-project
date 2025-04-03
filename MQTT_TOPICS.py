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

# Charger publish topics
TOPIC_MOVEMNT = "10/charger/movement"

#
# Charger Request
#

TOPIC_REQUEST_CHARGE = "10/charger/request_charge" # msg filed
TOPIC_RESPONSE_CHARGE = "10/charger/response_charge" # msg filed: yes/no

#
# Scooter Request
# 


#
# Server Topics
#

TOPIC_DISCOUNT = "10/server/discount" # msg filed: valuse of discount given (x%)
