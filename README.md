## TTM4115 project Spring 2025

### ``` state_machines ``` - folder:

#### To run, files contained in ``` state_machines ``` folder need the following python libraries:
* matplotlib
* stmpy
* phao-mqtt
* Flask 

After installing required dependencies:

File ```/state_machines/charger_stm.py ``` should be placed in a Raspberry Pi with a Parallax PIR Motion Sensor (Rev B). It can be started by running ```python3 state_machines/charger_stm.py```.

The other ```/state_machines/* ``` files should be placed in a Raspberry Pi with Sense HAT V2”. They can be started by running ```python3 state_machines/flask_server.py``.

### ``` app ``` - folder: 
#### To run, files contained in ``` app ``` folder need the following python libraries:

* kivy
* opencv-python
* pyzbar
* kivy-garden
* kivy_garden.mapview

After installing required dependencies User App can be started by running ```python3 app/user_app.py ```.
