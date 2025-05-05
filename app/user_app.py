import ctypes                                           # Needed to read windows property
import platform                                         # Needed to check if we are on Windows
import kivy                                             # Import Kivy
from kivy.app               import App                  # primary kivy lib
from kivy.core.window       import Window               # Needed for configuration of size of the display window
from kivy.uix.button        import Button               # Needed for setup of buttons
from kivy.uix.floatlayout   import FloatLayout          # Needed for an easy to modify display
from kivy.uix.image         import Image                # Needed for display of what the camera sees
from kivy.graphics          import Rectangle, Color     # Needed for UI setup
from kivy.graphics.texture  import Texture              # Needed for conversion from raw camera data to display image
from kivy.clock             import Clock                # Needed for camera fps config
import cv2                  as Camera                   # Needed for camera capture
from pyzbar.pyzbar          import decode               # Needed for qr code decoding from image
from kivy_garden.mapview    import MapView, MapMarker   # Needed for map display
import paho.mqtt.client     as MQTT                     # Needed for IoT communication
import json                                             # Needed for packet reading and creation
from random                 import random               # Needed for Testing
from kivy.uix.popup         import Popup                # Needed for Popup
from kivy.uix.label         import Label                # Needed for Popup Title
from kivy.config            import Config               # Needed for fixing some display issues
from kivy.uix.boxlayout     import BoxLayout            # Needed for Popup Display
from kivy.uix.textinput     import TextInput            # Needed for Username

# Function needed to fix an issue on Windows
def win_scale():
    # If system is not windows keep native scale
    if platform.system() != 'Windows':
        return 1
    # If system is Windows, Get and calculate how much to multiply UI Objects
    return ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100

#MQTT Topics used in the app
MQTT_TOPIC_TO_SERVER                = '10/to_server'
MQTT_TOPIC_FROM_SERVER_TO_USER_APPS = '10/from_server_to_user_apps'
MQTT_TOPIC_SCOOTER_STATUS           = '10/scooter_status'

# State-Machine State Defines
STATE_IDLE = 1  
STATE_SCAN = 2  
STATE_DRIV = 3  
STATE_CHCK = 4   

# Size of the app window
WIN_HEIGHT  = 700
WIN_WIDTH   = 400

# Configuration of the app window
Config.set('graphics', 'allow_hidpi', '0')
Window.size = (400, 700)
Window.size_hint = (None, None)
Window.borderless = False
Window.resizable = False

class MQTT_MANAGER():
    def __init__(self, topic, username):
        # Main Connection Paramerters
        self.MQTT_BROKER    = 'mqtt20.iik.ntnu.no'
        self.MQTT_PORT      = 1883

        # A Queue for the incomming msg to the MQTT Module
        self.command_arr = []

        # App Username is stored in the MQTT Module
        self.username = username

        # Set the current topic that MQTT is connected to
        self.CURRENT_TOPIC = topic

        # Usual Init of MQTT module
        self.Client = MQTT.Client()

        self.Client.on_connect = self.on_connect
        self.Client.on_message = self.on_message

        self.Client.connect(self.MQTT_BROKER, self.MQTT_PORT)
        self.Client.subscribe(self.CURRENT_TOPIC)

        self.Client.loop_start()

    # On incoming message save it to the queue
    def on_message(self, client, userdata, msg):
        try:
            self.payload = json.loads(msg.payload.decode('utf-8'))
            self.command_arr.append(self.payload)
        except:
            return None

    # Function used to get a command from the queue, FIFO format
    def get_msg(self):
        try:
            command = self.command_arr[0]
            self.command_arr.pop(0)
            return command
        except:
            return 0
        
    # Function for getting the username
    def get_username(self):
        return self.username
    
    # Function for setting the username
    def set_username(self, username):
        self.username = username
            
    # Function for behaviour at connection to the topic
    def on_connect(self, client, userdata, flags, rc):
        print(f'MQTT Connected to {self.MQTT_BROKER} at port:{self.MQTT_PORT} and topic: {self.CURRENT_TOPIC}')

# Extension of Kivy.MapView class MapMarker
class AdvMapMarker(MapMarker):
    # Initialization of the scooter marker
    # Makes it possible to store additional information about hte scooter
    def __init__(self, marker_id, scooter_state, **kwargs):
        super().__init__(**kwargs)
        self.marker_id = f'{marker_id}'
        self.scooter_state = scooter_state
        self.selected = 0

    # Functionality executed on release
    def on_release(self):
        self.selected = not self.selected
        print(f"Marker ID: {self.marker_id}")
        return self.marker_id

# Run at program start to calculate UI scaling
WINDOW_SCALING = win_scale()

class ScooterAppApp(App):

# What to do on start-up, runs after build
    def on_start(self):
        print("Initializing App...")

        # Map Parameters focused on trondheim
        # Needed for proper display of data from server
        self.d_lat = 63.447261-63.389189
        self.d_lon = 10.476090-10.329052

        self.s_lat = 63.447261
        self.s_lon = 10.476090

        self.map_dim = (1, 1)

        # Used for finding out which scooter was selected last
        self.last_selected = 0

        # Initialize MQTT
        # MQTT_Client is used for communication with the server
        # MQTT_ScooterStatus is used to communicate with Scooters 
        self.MQTT_Client        = MQTT_MANAGER(MQTT_TOPIC_TO_SERVER, 'username')
        self.MQTT_ScooterStatus = MQTT_MANAGER(MQTT_TOPIC_SCOOTER_STATUS,'name')

        self.MQTT_Client.Client.subscribe(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS)

        # Variable needed for state machine, "Current State"
        self.C_STATE = STATE_IDLE

        # Variables Explained by Index
        # 0 - Main Button Pressed
        # 1 - Multi User Select
        # 2 - Scooter Error
        # 3 - Checkout Flag
        self.STATE_MACHINE_CONTROL_REGISTER = [0, 0, 0, 0]
        
        # Variable Stores the read QR Message
        self.QR_MSG  = 0

        # List for keeping track of selected scooters
        self.SELECTED_SCOOTER_LIST = [None]

        # Clocks execute given function after given amount of time, repetable
        Clock.schedule_interval(self.state_machine_loop             , 0.05)
        Clock.schedule_interval(self.verify_scooter_marker_press    , 0.05)
        Clock.schedule_interval(self.update_scooter_icons           , 0.05)
        Clock.schedule_interval(self.process_scooter_communication  , 0.05)
        Clock.schedule_interval(self.mqtt_msg_process               , 0.05)
        Clock.schedule_interval(self.update_display                 , 1/60)

        # This Clock is  assigned as variables so it is possible to stop/cancel them
        self.clk_req             = Clock.schedule_interval(self.request_map_update, 10)

        # List of markers/scooters present on the map
        self.SCOOTER_MARKER_LIST = [None]

    # Main Function for creation and construciton of App
    def build(self):

        # Merged into the window, main layout form aka how things are placed
        # Size set to match window
        self.layout = FloatLayout(size=(WIN_WIDTH, WIN_HEIGHT))

        # UI Elementss
        # If any element has a property on_press it is associated with a function which
        # as the name suggests executes code on press of said element.
        # Most of the time they are connected to the control register.

        # Element Needed to display Camera for feedback with the QR Scanning
        self.cam_disp = Image(
            pos  = (50*WINDOW_SCALING , 200*WINDOW_SCALING), 
            size = (300*WINDOW_SCALING, 300*WINDOW_SCALING), 
            size_hint = (None, None),
            opacity = 0
        )

        # Element for Displaying of the map
        # Scooter and Charging station icons are added here
        self.map_disp = MapView(
            zoom = 11,
            lat = 63.446827, 
            lon = 10.4219,
            size_hint = (None, None),
            size = (400*WINDOW_SCALING, 550*WINDOW_SCALING),
            pos = (0*WINDOW_SCALING, 75*WINDOW_SCALING)
        )

        # Button for renting multiple scooters at the same time
        self.btn_group_rent = Button(
            text = 'Group\n Rent',
            size_hint = (None, None),
            size = (60*WINDOW_SCALING, 60*WINDOW_SCALING),
            pos  = (30*WINDOW_SCALING, 45*WINDOW_SCALING),
            on_press = self.btn_group_rent_fnc
        )

        # Button in the center of the screen
        self.btn_center = Button(
            text = 'Scan',
            size_hint=(None, None),
            size = (60*WINDOW_SCALING, 60*WINDOW_SCALING),
            pos = (170*WINDOW_SCALING, 45*WINDOW_SCALING),
            on_press = self.btn_center_fnc
        )

        # Button for viewing the profile
        self.btn_profile = Button(
            text='Profile',
            size_hint=(None, None),
            size = (60*WINDOW_SCALING, 60*WINDOW_SCALING),
            pos = (30*WINDOW_SCALING, 595*WINDOW_SCALING),
            on_press = self.btn_profile_fnc
        )

        # Button to add another scooter by scanning it rather than pressing on the map
        self.btn_add_multiple = Button(
            text = '+',
            size_hint=(None, None),
            size=(45*WINDOW_SCALING, 45*WINDOW_SCALING),
            pos=(37*WINDOW_SCALING,110*WINDOW_SCALING),
            opacity = 0,
            on_press = self.btn_add_multiple_fnc
        )

        # Element used to read from the camera, 0 means that it defaults to primary system camera
        # Clock is used to execute camera function at 30FPS
        self.cam = Camera.VideoCapture(0)
        Clock.schedule_interval(self.camera_update, 1.0/30.0)

        # Background images for the UI
        with self.layout.canvas.before:
            self.color_upd   = Color(0.368, 0.678, 0.949, 1)
            self.bottom_menu = Rectangle(
                pos =(0, 0),
                size=(WIN_WIDTH*WINDOW_SCALING, 75*WINDOW_SCALING))

            self.color_upd   = Color(0.368, 0.498, 0.945, 1)
            self.top_menu    = Rectangle(
                pos =(0*WINDOW_SCALING          , 625*WINDOW_SCALING),
                size=(WIN_WIDTH*WINDOW_SCALING  , 75*WINDOW_SCALING))

        # Add all of the UI Elements to the display layout
        self.layout.add_widget(self.map_disp)
        self.layout.add_widget(self.cam_disp)
        self.layout.add_widget(self.btn_group_rent)
        self.layout.add_widget(self.btn_profile)        
        self.layout.add_widget(self.btn_center)
        self.layout.add_widget(self.btn_add_multiple)

        # Create the display
        return self.layout
        

    ######################################################################
    ###                                                                ###
    ###                     STATE MACHINE FUNCTIONS                    ###
    ###                                                                ###
    ######################################################################

    def idle_app(self):
        # If scooter list empty keep it as scan, if some data is present, change it to start
        if self.SELECTED_SCOOTER_LIST[0] == (None or 0) and len(self.SELECTED_SCOOTER_LIST) == 1:
            self.btn_center.text = 'Scan'
        else:
            self.btn_center.text = 'Start'

        # Disable the camera
        self.cam_disp.opacity = 0

        # State Transition Logic
        # Check if main button was pressed
        # Depending on other paramerters check if it needs to scan of if it needs to Start the ride
        if self.STATE_MACHINE_CONTROL_REGISTER[0]:
            self.STATE_MACHINE_CONTROL_REGISTER[0] = 0
            if self.btn_center.text == ('Scan' or 'Add'):
                self.QR_MSG = 0
                return STATE_SCAN
            elif self.btn_center.text == 'Start':
                self.start_ride()
                return STATE_DRIV
        # If none of the cases were true, Stay in idle
        return STATE_IDLE

    # Set the camera to visible and keep it open untill it has detected a valid QR code
    def scan_app(self):
        self.cam_disp.opacity = 1
        if self.QR_MSG != 0:
            self.scooter_arr_add(self.QR_MSG)
            return STATE_IDLE
        return STATE_SCAN

    # Disable the camera and set the button text to End
    def driv_app(self):
        self.cam_disp.opacity = 0
        self.btn_center.text = 'End'
        # If the scooter data sent to the server was wrong, display error and return to idle
        if self.STATE_MACHINE_CONTROL_REGISTER[2]:
            popup = Popup(title='ERROR', 
                          content=Label(text='Scooter Already Booked.'), 
                          size_hint=(None, None),
                          size=(400,200)
                    )
            popup.open()
            # Disable Drive State
            self.STATE_MACHINE_CONTROL_REGISTER[2] = 0
            return STATE_IDLE
        
        # If main button was pressed and previous cases when through end the ride
        if self.STATE_MACHINE_CONTROL_REGISTER[0]:
            self.stop_ride()
            return STATE_CHCK
        return STATE_DRIV

    # Wait for Server to reply with confirmation for ending of ride and then return to idle
    # Otherwise wait for the msg
    def chck_app(self):
        if self.STATE_MACHINE_CONTROL_REGISTER[3]:
            # Create a popup and inform the user of end of ride
            popup = Popup(title='Ride Complete',
                          content=Label(text='Ride Complete Thank you!'),
                          size_hint=(None, None),
                          size=(400,200)
                    )
            popup.open()
            # Reset control register variables
            self.STATE_MACHINE_CONTROL_REGISTER[0] = 0
            self.STATE_MACHINE_CONTROL_REGISTER[3] = 0
            return STATE_IDLE
        return STATE_CHCK

    ######################################################################
    ###                                                                ###
    ###                        BUTTON FUNCTIONS                        ###
    ###                                                                ###
    ######################################################################

    # If button pressed set control register to high
    def btn_center_fnc(self, instance):
        self.STATE_MACHINE_CONTROL_REGISTER[0] = 1

    # if button pressed both set control register to high and change its color
    def btn_group_rent_fnc(self, instance):
        print("GROUP SELECT Pressed ...")
        self.STATE_MACHINE_CONTROL_REGISTER[1] = not self.STATE_MACHINE_CONTROL_REGISTER[1]
        
        if self.STATE_MACHINE_CONTROL_REGISTER[1]:
            self.btn_group_rent.background_color = 'green'
        else:
            self.btn_group_rent.background_color = 'gray'

    # TODO: Just connect it so it sends to scan state again
    # TODO: Make visible only when 1 scanned and group rent selected
    def btn_add_multiple_fnc(self, instance):
        print("Pressed +")
    
    # When pressed create a popup which lets the user modify their username
    def btn_profile_fnc(self, instance):
        # Handles UI creation separately from the build function
        self.popup = Popup(title='Profile Settings',
                          content=BoxLayout(orientation = 'vertical', padding=5, spacing=5),
                          size_hint=(None, None),
                          size=(200,400)
                    )
        self.txt_in = TextInput(multiline=False, size_hint=(1,0.6), text=self.MQTT_Client.get_username())
        
        # Creates Internal Confirm button and attaches a function to it
        self.btn_profile_cnf = Button(text='Confirm Changes', size_hint=(1,0.2))
        self.btn_profile_cnf.bind(on_release=self.confirm_profile_name_update)
        self.popup.content.add_widget(self.txt_in)
        self.popup.content.add_widget(self.btn_profile_cnf)

        # Opens/Displays the Popup
        self.popup.open()

    ######################################################################
    ###                                                                ###
    ###                       OTHER APP FUNCTIONS                      ###
    ###                                                                ###
    ######################################################################

    # Function run when the button is pressed on the profile username update
    def confirm_profile_name_update(self, instance):
        # Sets the username in the MQTT Client
        self.MQTT_Client.set_username(self.txt_in.text)
        
        # Closes the popup
        self.popup.dismiss()

    # Every 0.05s iterates over the SCOOTER_MARKER_LIST and checks if the scooter markers need to be updated
    def update_scooter_icons(self, dt):
        for scooter in self.SCOOTER_MARKER_LIST:
            # Shield in case of errors
            if scooter != None:
                # If the scooter is on any of the two states est it to visible and apply correct graphic
                if scooter.scooter_state == 'is_free' or scooter.scooter_state == 'in_use':
                    scooter.opacity = 1 
                    if   scooter and scooter.marker_id in self.SELECTED_SCOOTER_LIST:
                        scooter.source = 'scooter_marker_scanned.PNG'
                    else:
                        scooter.source = 'scooter_marker.PNG'
                # Otherwise Use a "transparent" graphic and set its size to 1x1 px
                # Basically invisible
                else:
                    scooter.source = 'scooter_none.PNG'
                    scooter.size = (1,1)


    # Processes if the markers/scooter have been selected and adds processes them accordingly
    def verify_scooter_marker_press(self, dt):
        # Temporary list of the markers that have been selected/pressed by the user
        temp_selected_list = []

        # Iterates over the list of all the markers and adds the ones that have been selected
        # by the user to the temp list
        for marker in self.SCOOTER_MARKER_LIST:
            if marker is not None and marker.selected:
                temp_selected_list.append(marker)

        # If "Group Select" is set to true add multiple to the selected scooter list
        if self.STATE_MACHINE_CONTROL_REGISTER[1]:
            for sc in temp_selected_list:
                if sc.marker_id not in self.SELECTED_SCOOTER_LIST:
                    self.SELECTED_SCOOTER_LIST.append(sc.marker_id)
        
        # Otherwise find the most recent pressed scooter and add it at the start of the list
        else:
            try:
                # Check that the size of the list is larger then initial size (1)
                if len(temp_selected_list) > 1:
                    for mk in temp_selected_list:
                        if mk.marker_id != self.last_selected:
                            self.last_selected = mk.marker_id
                            break
                # if the size is the same as initial set the last selected as that one
                elif len(temp_selected_list) == 1:
                    self.last_selected = temp_selected_list[-1].marker_id

                # Reset the rest of the scooters from the list to not selected since we are in
                # single ride select 
                for mk in temp_selected_list:
                    if mk.marker_id != self.last_selected and self.last_selected != 0:
                        mk.selected = 0

                # Update the first postition on the select array with the last selected scooter
                self.SELECTED_SCOOTER_LIST[0] = self.last_selected
            
            # If nothing matched or any other error reset the selected scooter list
            except:
                self.SELECTED_SCOOTER_LIST = [None]

    # Due to a bug with MapView this function forces the MapView to update the location of scooters
    # and adding them to the display by simulating a move of the map.
    # It is assigned to one of the clocks and updates in a rate of 60FPS
    def update_display(self, dt):
        self.map_disp.center_on(self.map_disp.lat, self.map_disp.lon)


    # Main function for processing incoming communication from the server
    # This function is triggered every 0.05s to not make the queue overflow
    def mqtt_msg_process(self, dt):
        # Gets msg from the MQTT Client
        msg = self.MQTT_Client.get_msg()
        try:
            # If the msg contains any valuable data, check if this is the correct user
            if msg is not 0 and msg['user_name'] == self.MQTT_Client.username:
                try:
                    # This if-else is setup to process all app specific commands
                    # This command is focused on getting the initial data from the server
                    
                    # After the data has been recived it stops the clock responsible for
                    # sending the requests for said data
                    if msg['msg'] == 'scooter_information':
                    
                        # Updates dimension of the map so it is possible to scale the server values
                        # to their real life counterparts, longitude and langitude
                        print("Updating Map Dims...")
                        x_dim = msg['x_dim']
                        y_dim = msg['y_dim']
                        self.map_dim = (int(x_dim), int(y_dim))

                        # The msg also includes the information about where the charging station
                        # is located
                        cs_x = msg['charger_x']
                        cs_y = msg['charger_y']

                        # Calculate Charging station longitude and latitude
                        cs_lat = self.s_lat - int(cs_y)/self.map_dim[1]*self.d_lat
                        cs_lon = self.s_lon + int(cs_x)/self.map_dim[0]*self.d_lon - self.d_lon

                        # Adds the Charging station to the map
                        self.map_disp.add_widget(self.create_cg(cs_lat, cs_lon))

                        # Stops the clock
                        Clock.unschedule(self.clk_req)
                        print("Stoping clocks...")
                    
                    # Both of the two next commands are focused on removing the scooter that has been
                    # selected by another user and therefore is not avaible here.
                    elif msg['msg'] == 'single_not_available':
                        print("Error...")
                        self. remove_missmatch_scooters(msg['scooter_name'])
                    elif msg['msg'] == 'multiple_not_available':
                        print("Error...")
                        self. remove_missmatch_scooters(msg['scooter_names'])

                    # Ack that the booking/ride was successfuly ended, sets the bit in the control register
                    # that it might exit the state/execute related functionality
                    elif msg['msg'] == ('ack_end_book_single' or 'ack_end_book_multiple'):
                        print("Ride Ended Checkout...")
                        self.STATE_MACHINE_CONTROL_REGISTER[3] = 1
                except:
                    # If something went wrong exit
                    return
        # If msg was of wrong format, do nothing
        except:
            None

    # Remove the already booked scooters from the selected list based on server information
    def remove_missmatch_scooters(self, sc_list):
        # Update the control register bit to inform the state machine that the provided data was wrong
        self.STATE_MACHINE_CONTROL_REGISTER[2] = 1
        
        # Iterate over the scooter list that was recived from the server and remove any 
        # matches from from the ones that the user has selected
        for sc in sc_list:
            if sc in self.SELECTED_SCOOTER_LIST:
                self.SELECTED_SCOOTER_LIST.remove(sc)
                self.remove_from_selected(sc)

    # Remove the select status as from them as well, this is needed because the msg from the server
    # is a string, this function locates the scooters based on said string and updates their information
    def remove_from_selected(self, item):
        for ic in self.SCOOTER_MARKER_LIST:
            if ic is not None and ic.marker_id == item:
                ic.selected = 0
                return

    # This function is executed every 0.05s and is connected to the other MQTT Client
    # This Client focuses on processing the incomming data from the scooters to update
    # their information
    def process_scooter_communication(self, dt):
        # Get msg from client
        scooter_msg = self.MQTT_ScooterStatus.get_msg()

        # Check if it includes any valuable data
        if scooter_msg is not 0:

            # Calculate scooter position on the map
            print("Scooter Info Update...")
            
            sc_lat = self.s_lat - int(scooter_msg['y'])/self.map_dim[1]*self.d_lat
            sc_lon = self.s_lon + int(scooter_msg['x'])/self.map_dim[0]*self.d_lon - self.d_lon

            # Create temporary marker
            temp_mark = self.create_scooter_marker(sc_lat, sc_lon, scooter_msg['name'], scooter_msg['state'])

            # Iterate over the list of avaible markers
            for sc in self.SCOOTER_MARKER_LIST:
                # Shiled
                if sc is not None:
                    # If a match was found update the information and exit the function 
                    if temp_mark.marker_id == sc.marker_id:
                        sc.lat = sc_lat
                        sc.lon = sc_lon
                        sc.size = (50, 50)
                        sc.scooter_state = temp_mark.scooter_state
                        return
            # If there was no match for any of the scooters add the temporary scooter to the map
            self.SCOOTER_MARKER_LIST.append(temp_mark)
            self.map_disp.add_widget(temp_mark)

    # Creates a MQTT request and sends it to the server in order to get initial map data
    def request_map_update(self, dt):
        print('Requesting Map Config...')

        mqtt_req = {"msg":"scooterlist_request", "user_name":self.MQTT_Client.get_username()}
        self.MQTT_Client.Client.publish(MQTT_TOPIC_TO_SERVER, json.dumps(mqtt_req))

    # This is the main state machine loop, it checks every 0.05s for updates and responses from
    # the defined functions to decide how it should adjust itself.
    # It is made to function with both new and old versions of Python3
    def state_machine_loop(self, dt):
        # Main State Machine loop
        # Assumes Python >= 3.10
        try:
            match self.C_STATE:
                case 1: 
                    self.C_STATE = self.idle_app()
                case 2: 
                    self.C_STATE = self.scan_app()
                case 3: 
                    self.C_STATE = self.driv_app()
                case 4: 
                    self.C_STATE = self.chck_app()
                case _: # "Default/Else Case"
                    self.C_STATE = STATE_IDLE
        # Python < 3.10
        except:
            if self.C_STATE == STATE_IDLE:
                self.C_STATE = self.idle_app()
            elif self.C_STATE == STATE_SCAN:
                self.C_STATE = self.scan_app()
            elif self.C_STATE == STATE_DRIV:
                self.C_STATE = self.driv_app()
            elif self.C_STATE == STATE_CHCK:
                self.C_STATE = self.chck_app()
            else:
                self.C_STATE = STATE_IDLE


    # Code for constructing the msg which is sent to the server on ride start 
    def start_ride(self):
        mqtt_msg_base = 0

        if self.STATE_MACHINE_CONTROL_REGISTER[1]:
            if self.SELECTED_SCOOTER_LIST[0] is None:
                self.SELECTED_SCOOTER_LIST.pop(0)
            
            scooter_names = []

            for sc in self.SELECTED_SCOOTER_LIST:
                if sc != (0 and None):
                    scooter_names.append(sc)
                

            mqtt_msg_base = {'msg': 'book_multiple', 'scooter_names':scooter_names                 , 'user_name': self.MQTT_Client.get_username()}
        else:
            mqtt_msg_base = {'msg': 'book_single'  , 'scooter_name' :self.SELECTED_SCOOTER_LIST[-1], 'user_name': self.MQTT_Client.get_username()}
        
        msg = json.dumps(mqtt_msg_base)

        self.MQTT_Client.Client.publish(MQTT_TOPIC_TO_SERVER, msg)

    # Code for construcing the msg which is sent to the server, on ride end
    def stop_ride(self):
        mqtt_msg_base = 0
        if self.STATE_MACHINE_CONTROL_REGISTER[1]:
            if self.SELECTED_SCOOTER_LIST[0] is None:
                self.SELECTED_SCOOTER_LIST.pop(0)

            scooter_names = []

            for sc in self.SELECTED_SCOOTER_LIST:
                if sc != 0 and sc != None:
                    scooter_names.append(sc)

            mqtt_msg_base = {'msg': 'end_book_multiple' , 'scooter_names': scooter_names                 , 'user_name': self.MQTT_Client.get_username()}
        else:
            mqtt_msg_base = {'msg': 'end_book_single'   , 'scooter_name' : self.SELECTED_SCOOTER_LIST[-1], 'user_name': self.MQTT_Client.get_username()}
        
        self.SELECTED_SCOOTER_LIST = [None]

        self.remove_selected_all()

        self.MQTT_Client.Client.publish(MQTT_TOPIC_TO_SERVER, json.dumps(mqtt_msg_base))
    
    # Resets the entire app and any selected scooter
    def remove_selected_all(self):
        for sc in self.SCOOTER_MARKER_LIST:
            if sc is not None:
                sc.selected = 0
        self.last_selected = 0

    # This function processes the QR Code and looks for a matching scooter id
    # If a match has been found it adds said scooter as the selected scooter
    def scooter_arr_add(self, QR_MSG):
        try:
            # Read the msg and center the camera on the provided scooter
            QR_Content = json.loads(QR_MSG)
            self.center_scooter(QR_Content['name'])
            
            # If "Group Rent" is set to true add it as part of list otherwise set the scooter
            # as first position in the list
            if self.STATE_MACHINE_CONTROL_REGISTER[1]:
                if QR_Content['name'] not in self.SELECTED_SCOOTER_LIST: 
                    self.SELECTED_SCOOTER_LIST.append(QR_Content['name'])
            else:
                self.SELECTED_SCOOTER_LIST[0] = QR_Content['name']
        except:
            # Most common error in this case is that the QR code was invalid, print it to the console
            print("Invalid QR Code")

    # This function iterates over the list of all scooter markers untill it finds a match
    # then it moves the camera and zooms it in on the scooter that was scanned
    def center_scooter(self, qr_msg):
        print(f"Re-centering for {qr_msg}")
        for sc in self.SCOOTER_MARKER_LIST:
            # If match found update camera position
            if sc != None and qr_msg == sc.marker_id:
                print(f"Camera Position Update... {sc}")
                self.map_disp.lon=sc.lon
                self.map_disp.lat=sc.lat
                self.map_disp.zoom = 13
                # Mark the scooter as selected
                sc.selected = 1
        
        
    # Function to simplify the process of creating a scooter icon
    def create_scooter_marker(self, lat_l, lon_l, scooter_id, scooter_state):
        scooter_marker = AdvMapMarker(lat=lat_l, lon=lon_l, size_hint=(None, None), marker_id=scooter_id, scooter_state=scooter_state)
        scooter_marker.source = 'scooter_marker.PNG'
        scooter_marker.width = 50
        scooter_marker.height = 50
        return scooter_marker

    # Function to simplify the process of creating a charging station icon
    def create_cg(self, lat_l, lon_l):
        charging_s = MapMarker(lat=lat_l, lon=lon_l, size_hint=(None, None))
        charging_s.source = 'charging_station.PNG'
        charging_s.width = 50
        charging_s.height = 50
        return charging_s

    # What the camera is supposed to do 
    def camera_update(self, frame):
        ret, frame = self.cam.read()

        if ret:
            grx = self.frame_to_texture(frame)
            self.cam_disp.texture = grx
            qr_objects = decode(frame)

            # Decode the QR code into its original data
            for o in qr_objects:
                qr_data = o.data.decode('utf-8')
                print(f'QR Code Data: {qr_data}')
                self.QR_MSG = qr_data

    # Convert the frame captured by the camera and display it back to the user
    def frame_to_texture(self, frame):
        frame = Camera.cvtColor(frame, Camera.COLOR_BGR2RGB)
        frame = Camera.flip(frame, 0)
        frame = Camera.flip(frame, 1)
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
        texture.blit_buffer(frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        return texture

# Starts the app
ScooterAppApp().run()
