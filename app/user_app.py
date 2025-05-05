import ctypes                                           # Needed to read windows property
import platform                                         # Needed to check if we are on Windows
import kivy
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
from kivy.uix.popup         import Popup
from kivy.uix.label         import Label
from kivy.config            import Config
from kivy.uix.boxlayout     import BoxLayout
from kivy.uix.textinput     import TextInput

def win_scale():
    if platform.system() != 'Windows':
        return 2
    return ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100

WINDOW_SCALING = win_scale()

MQTT_TOPIC_TO_SERVER = '10/to_server'
MQTT_TOPIC_FROM_SERVER_TO_USER_APPS = '10/from_server_to_user_apps'
MQTT_TOPIC_SCOOTER_STATUS = '10/scooter_status'

# State-Machine State Defines
STATE_EXIT = 0  # 
STATE_IDLE = 1  # 
STATE_SCAN = 2  # 
STATE_DRIV = 3  # 
STATE_CHCK = 4  # 
STATE_RESV = 5  # 

WIN_HEIGHT  = 700
WIN_WIDTH   = 400

# Temporary, needed for testing
scooter_cnt = 0

Config.set('graphics', 'allow_hidpi', '0')
Window.size = (400, 700)
Window.size_hint = (None, None)
Window.borderless = False
Window.resizable = False

class MQTT_MANAGER():
    def __init__(self, topic, username):
        self.MQTT_BROKER    = 'mqtt20.iik.ntnu.no'
        self.MQTT_PORT      = 1883

        self.username = username

        self.command_arr = []

        self.CURRENT_TOPIC = topic

        self.Client = MQTT.Client()

        self.Client.on_connect = self.on_connect
        self.Client.on_message = self.on_message

        self.Client.connect(self.MQTT_BROKER, self.MQTT_PORT)
        self.Client.subscribe(self.CURRENT_TOPIC)

        self.Client.loop_start()
    
    def sub_topic(self, topic):
        self.Client.subscribe(topic)

    def unsub_topic(self, topic):
        self.Client.unsubscribe(topic)

    def change_topic(self, topic):
        self.Client.unsubscribe(self.CURRENT_TOPIC)
        self.Client.subscribe(topic)
        self.CURRENT_TOPIC = topic

    def on_message(self, client, userdata, msg):
        try:
            self.payload = json.loads(msg.payload.decode('utf-8'))
        except:
            return None
        
        self.command_arr.append(self.payload)

    def get_msg(self):
        try:
            cmd = self.command_arr[0]
            self.command_arr.pop(0)
            return cmd
        except:
            return 0
        
    def get_username(self):
        return self.username
    
    def set_username(self, username):
        self.username = username
            
    def on_connect(self, client, userdata, flags, rc):
        print(f'MQTT Connected to {self.MQTT_BROKER} at port:{self.MQTT_PORT} and topic: {self.CURRENT_TOPIC}')

    def post_msg(self, msg):
        self.Client.publish(MQTT_TOPIC_TO_SERVER,msg)

#TODO: ADD function of starting/select from the map | DONE~
#TODO: ADD functionality to the onclick function    | DONE
#? Since its part of MapMarker, it should be possible to integrate it into the App self. and then somehow get pressed scooter id into that?
class AdvMapMarker(MapMarker):
    def __init__(self, marker_id, scooter_state, **kwargs):
        super().__init__(**kwargs)
        self.marker_id = f'{marker_id}'
        self.scooter_state = scooter_state
        self.selected = 0

    def on_release(self):
        self.on_click()

    def on_click(self):
        self.selected = not self.selected
        print(f"Marker ID: {self.marker_id}")
        return self.marker_id

class ScooterAppApp(App):

    def verify_icon_press(self, dt):
        selected_list = []

        for marker in self.scooter_list:
            if marker is not None and marker.selected:
                selected_list.append(marker)

        if self.C_STATE_CTRL[2]:
            for sc in selected_list:
                if sc.marker_id not in self.C_SCOOTER_LIST:
                    self.C_SCOOTER_LIST.append(sc.marker_id)
        else:
            try:
                if len(selected_list) > 1:
                    for mk in selected_list:
                        if mk.marker_id != self.last_selected:
                            self.last_selected = mk.marker_id
                            break
                elif len(selected_list) == 1:
                    self.last_selected = selected_list[-1].marker_id

                for mk in selected_list:
                    if mk.marker_id != self.last_selected and self.last_selected != 0:
                        mk.selected = 0

                self.C_SCOOTER_LIST[0] = self.last_selected
            except:
                self.C_SCOOTER_LIST = [None]

    # Main Function for creation and construciton of App
    #!SHOULD BE DONE
    def build(self):
        # Move it Later
        self.scooter_list = [None]

        Config.set('graphics', 'allow_hidpi', '0')

        self.layout = FloatLayout(size=(WIN_WIDTH, WIN_HEIGHT))

        # UI Elements

        self.cam_disp = Image(
            pos  = (50*WINDOW_SCALING , 200*WINDOW_SCALING), 
            size = (300*WINDOW_SCALING, 300*WINDOW_SCALING), 
            size_hint = (None, None),
            opacity = 0
        )

        self.map_disp = MapView(
            zoom = 11,
            lat = 63.446827, 
            lon = 10.4219,
            size_hint = (None, None),
            size = (400*WINDOW_SCALING, 550*WINDOW_SCALING),
            pos = (0*WINDOW_SCALING, 75*WINDOW_SCALING)
        )

        self.btn_group_rent = Button(
            text = 'Group\n Rent',
            size_hint = (None, None),
            size = (60*WINDOW_SCALING, 60*WINDOW_SCALING),
            pos  = (30*WINDOW_SCALING, 45*WINDOW_SCALING),
            on_press = self.btn_group_rent_fnc
        )

        self.btn_center = Button(
            text = 'Scan',
            size_hint=(None, None),
            size = (60*WINDOW_SCALING, 60*WINDOW_SCALING),
            pos = (170*WINDOW_SCALING, 45*WINDOW_SCALING),
            on_press = self.btn_center_fnc
        )

        self.btn_profile = Button(
            text='Profile',
            size_hint=(None, None),
            size = (60*WINDOW_SCALING, 60*WINDOW_SCALING),
            pos = (30*WINDOW_SCALING, 595*WINDOW_SCALING),
            on_press = self.btn_profile_fnc
        )

        self.btn_add_multiple = Button(
            text = '+',
            size_hint=(None, None),
            size=(45*WINDOW_SCALING, 45*WINDOW_SCALING),
            pos=(37*WINDOW_SCALING,110*WINDOW_SCALING),
            on_press = self.btn_add_multiple_fnc
        )

        self.cam            = Camera.VideoCapture(0)
        Clock.schedule_interval(self.camera_update, 1.0/30.0)

        with self.layout.canvas.before:
            self.color_upd   = Color(0.368, 0.678, 0.949, 1)
            self.bottom_menu = Rectangle(
                pos =(0, 0),
                size=(WIN_WIDTH*WINDOW_SCALING, 75*WINDOW_SCALING))

            self.color_upd   = Color(0.368, 0.498, 0.945, 1)
            self.top_menu    = Rectangle(
                pos =(0*WINDOW_SCALING          , 625*WINDOW_SCALING),
                size=(WIN_WIDTH*WINDOW_SCALING  , 75*WINDOW_SCALING))

        self.layout.add_widget(self.map_disp)
        self.layout.add_widget(self.cam_disp)
        self.layout.add_widget(self.btn_group_rent)
        self.layout.add_widget(self.btn_profile)        
        self.layout.add_widget(self.btn_center)
        self.layout.add_widget(self.btn_add_multiple)

        return self.layout
    
    # What to do on start up, sort of equivalent to __init__()
    def on_start(self):
        print("Initializing App...")

        self.last_selected = 0

        self.map_dim = (10, 10)

        self.d_lat = 63.447261-63.389189
        self.d_lon = 10.476090-10.329052

        self.s_lat = 63.447261
        self.s_lon = 10.476090

        # Initialize MQTT
        self.MQTT_Client        = MQTT_MANAGER(MQTT_TOPIC_TO_SERVER, 'username')
        self.MQTT_ScooterStatus = MQTT_MANAGER(MQTT_TOPIC_SCOOTER_STATUS,'name')

        self.MQTT_Client.sub_topic(MQTT_TOPIC_FROM_SERVER_TO_USER_APPS)

        # Variables needed for state machine
        self.C_STATE = 1

        #TODO: ADD implementation for each of the control bits ~ Pain and misery
        #Variables Explained
        # 0 - Scan Button Pressed
        # 1 - Profile Button Pressed
        # 2 - Multi User Select
        # 3 - Show Charging Station Pressed
        # 4 - Reserve  State
        # 5 - In Drive State
        # 6 - Scooter Error
        # 7 - Checkout Flag
        self.C_STATE_CTRL   = [0, 0, 0, 0, 0, 0, 0, 0]
        self.QR_MSG         = 0
        self.C_SCOOTER_LIST = [None]

        # Internal Kivy "Threads"
        Clock.schedule_interval(self.state_machine_loop , 0.05)
        Clock.schedule_interval(self.verify_icon_press  , 0.05)
        Clock.schedule_interval(self.update_icons       , 0.01)
        Clock.schedule_interval(self.process_com        , 0.01)
        self.dims_clk = Clock.schedule_interval(self.init_dims , 0.05)
        self.clk_req  = Clock.schedule_interval(self.update_map, 10)
        self.clk_map_disp_update = Clock.schedule_interval(self.update_display, 1/60)

    def update_display(self, dt):
        self.map_disp.center_on(self.map_disp.lat, self.map_disp.lon)

    def init_dims(self, dt):
        msg = self.MQTT_Client.get_msg()
        try:
            if msg is not 0 and msg['user_name'] == self.MQTT_Client.username:
                try:
                    if msg['msg'] == 'scooter_information':
                        print("Updating Map Dims...")
                        x_dim = msg['x_dim']
                        y_dim = msg['y_dim']
                        self.map_dim = (int(x_dim), int(y_dim))

                        cs_x = msg['charger_x']
                        cs_y = msg['charger_y']
                        cs_pos = self.calc_pos(cs_x, cs_y)

                        self.map_disp.add_widget(self.create_cg(cs_pos[0], cs_pos[1]))

                        print("Stoping clocks...")
                        #Clock.unschedule(self.dims_clk)
                        Clock.unschedule(self.clk_req)
                    elif msg['msg'] == 'single_not_available':
                        print("Error...")
                        self.remove_selected(msg['scooter_name'])
                    elif msg['msg'] == 'multiple_not_available':
                        print("Error...")
                        self.remove_selected(msg['scooter_names'])
                    elif msg['msg'] == 'ack_end_book_single' or 'ack_end_book_multiple':
                        print("Ride Ended Checkout...")
                        self.C_STATE_CTRL[7] = 1
                except:
                    return
        except:
            None

    def calc_pos(self, x, y):

        sc_lat = self.s_lat - int(y)/self.map_dim[1]*self.d_lat
        sc_lon = self.s_lon + int(x)/self.map_dim[0]*self.d_lon - self.d_lon

        return (sc_lat, sc_lon)

    def remove_selected(self, sc_list):
        self.C_STATE_CTRL[6] = 1
        for sc in sc_list:
            if sc in self.C_SCOOTER_LIST:
                self.C_SCOOTER_LIST.remove(sc)
                self.remove_from_selected(sc)

    def remove_from_selected(self, item):
        for ic in self.scooter_list:
            if ic is not None and ic.marker_id == item:
                ic.selected = 0
                return

    def process_com(self, dt):
        scooter_msg = self.MQTT_ScooterStatus.get_msg()

        if scooter_msg is not 0:

            print("Scooter Info Update...")
            # Scooter Position
            sc_lat = self.s_lat - int(scooter_msg['y'])/self.map_dim[1]*self.d_lat
            sc_lon = self.s_lon + int(scooter_msg['x'])/self.map_dim[0]*self.d_lon - self.d_lon

            temp_mark = self.create_scooter_marker(sc_lat, sc_lon, scooter_msg['name'], scooter_msg['state'])

            for sc in self.scooter_list:
                if sc is not None: 
                    if temp_mark.marker_id == sc.marker_id:
                        sc.lat = sc_lat
                        sc.lon = sc_lon
                        sc.size = (50, 50)
                        sc.scooter_state = temp_mark.scooter_state
                        return
            self.scooter_list.append(temp_mark)
            self.map_disp.add_widget(temp_mark)

    def update_map(self, dt):
        print('Requesting Map Config...')

        mqtt_req = {"msg":"scooterlist_request", "user_name":self.MQTT_Client.get_username()}
        self.MQTT_Client.Client.publish(MQTT_TOPIC_TO_SERVER, json.dumps(mqtt_req))

    def state_machine_loop(self, dt):
        match self.C_STATE:
            case 0: #STATE_EXIT
                self.C_STATE = STATE_EXIT
                self.stop()
            case 1: #STATE_IDLE
                self.C_STATE = self.idle_app()
            case 2: #STATE_SCAN
                self.C_STATE = self.scan_app()
            case 3: #STATE_DRIV
                self.C_STATE = self.driv_app()
            case 4: #STATE_CHCK
                self.C_STATE = self.chck_app()
            case _:
                self.C_STATE = STATE_IDLE

    # STATE MACHINE FUNCTIONS
    #TODO: ADD Functionality of other buttons and changing states in the state machine
    #TODO: DRAW New State Machine Diagram   | This is a mess ~ Done
    def idle_app(self):
        # Button text handler
        if (self.C_SCOOTER_LIST[0] == None or self.C_SCOOTER_LIST[0] == 0) and len(self.C_SCOOTER_LIST) == 1:
            self.btn_center.text = 'Scan'
        #elif self.C_STATE_CTRL[2]:
        #    self.btn_center.text = 'Add'
        else:
            self.btn_center.text = 'Start'

        self.cam_disp.opacity = 0

        # State Transition Logic
        if self.C_STATE_CTRL[0]:
            self.C_STATE_CTRL[0] = 0
            if self.btn_center.text == ('Scan' or 'Add'):
                self.QR_MSG = 0
                return STATE_SCAN
            elif self.btn_center.text == 'Start':
                self.start_ride()
                return STATE_DRIV
        return STATE_IDLE

    def scan_app(self):
        self.cam_disp.opacity = 1
        if self.QR_MSG != 0:
            self.scooter_arr_add(self.QR_MSG)
            return STATE_IDLE
        return STATE_SCAN

    def driv_app(self):
        self.cam_disp.opacity = 0
        self.btn_center.text = 'End'
        if self.C_STATE_CTRL[6]:
            popup = Popup(title='ERROR', 
                          content=Label(text='Scooter Already Booked'), 
                          size_hint=(None, None),
                          size=(200,200)
                    )
            popup.open()
            self.C_STATE_CTRL[6] = 0
            return STATE_IDLE
        
        if self.C_STATE_CTRL[0]:
            self.stop_ride()
            self.C_STATE_CTRL[5] = 0
            return STATE_CHCK
        return STATE_DRIV

    def chck_app(self):
        if self.C_STATE_CTRL[7]:
            popup = Popup(title='Ride Complete',
                          content=Label(text='Ride Complete Thank you <3'),
                          size_hint=(None, None),
                          size=(200,200)
                    )
            popup.open()
            self.C_STATE_CTRL[0] = 0
            return STATE_IDLE
        return STATE_CHCK

    def update_icons(self, dt):
        for scooter in self.scooter_list:
            if scooter != None:
                if scooter.scooter_state == 'is_free' or scooter.scooter_state == 'in_use':
                    scooter.opacity = 1 
                    if   scooter and scooter.marker_id in self.C_SCOOTER_LIST:
                        scooter.source = 'scooter_marker_scanned.PNG'
                    else:
                        scooter.source = 'scooter_marker.PNG'
                else:
                    scooter.source = 'scooter_none.PNG'
                    scooter.size = (1,1)

    # BUTTON FUNCTIONS
    def btn_center_fnc(self, instance):
        self.C_STATE_CTRL[0] = 1

    def btn_group_rent_fnc(self, instance):
        print("GROUP SELECT Pressed ...")
        self.C_STATE_CTRL[2] = not self.C_STATE_CTRL[2]
        if self.C_STATE_CTRL[2]:
            self.btn_group_rent.background_color = 'green'
        else:
            self.btn_group_rent.background_color = 'gray'

    def btn_add_multiple_fnc(self, instance):
        print("Pressed +")
    
    def btn_profile_fnc(self, instance):
        self.popup = Popup(title='Profile Settings',
                          content=BoxLayout(orientation = 'vertical', padding=5, spacing=5),
                          size_hint=(None, None),
                          size=(200,400)
                    )
        self.txt_in = TextInput(multiline=False, size_hint=(1,0.6), text=self.MQTT_Client.get_username())
        self.btn_profile_cnf = Button(text='Confirm Changes', size_hint=(1,0.2))
        self.btn_profile_cnf.bind(on_release=self.confirm_profile_name_update)
        self.popup.content.add_widget(self.txt_in)
        self.popup.content.add_widget(self.btn_profile_cnf)

        self.popup.open()

    def confirm_profile_name_update(self, instance):
        self.MQTT_Client.set_username(self.txt_in.text)
        self.popup.dismiss()
        print(self.MQTT_Client.get_username())

    # OTHER APP FUNCTIONS
    def start_ride(self):

        mqtt_msg_base = 0

        if self.C_STATE_CTRL[2]:
            if self.C_SCOOTER_LIST[0] is None:
                self.C_SCOOTER_LIST.pop(0)
            
            scooter_names = []

            for sc in self.C_SCOOTER_LIST:
                if sc != (0 and None):
                    scooter_names.append(sc)
                

            mqtt_msg_base = {'msg': 'book_multiple', 'scooter_names':scooter_names          , 'user_name': self.MQTT_Client.get_username()}
        else:
            mqtt_msg_base = {'msg': 'book_single'  , 'scooter_name' :self.C_SCOOTER_LIST[-1], 'user_name': self.MQTT_Client.get_username()}
        
        msg = json.dumps(mqtt_msg_base)

        self.MQTT_Client.Client.publish(MQTT_TOPIC_TO_SERVER, msg)

    def stop_ride(self):
        mqtt_msg_base = 0
        if self.C_STATE_CTRL[2]:
            if self.C_SCOOTER_LIST[0] is None:
                self.C_SCOOTER_LIST.pop(0)

            scooter_names = []

            for sc in self.C_SCOOTER_LIST:
                if sc != 0 and sc != None:
                    scooter_names.append(sc)

            mqtt_msg_base = {'msg': 'end_book_multiple' , 'scooter_names': scooter_names             , 'user_name': self.MQTT_Client.get_username()}
        else:
            mqtt_msg_base = {'msg': 'end_book_single'   , 'scooter_name' : self.C_SCOOTER_LIST[-1]   , 'user_name': self.MQTT_Client.get_username()}
        
        self.C_SCOOTER_LIST = [None]

        self.remove_selected_all()

        self.MQTT_Client.Client.publish(MQTT_TOPIC_TO_SERVER, json.dumps(mqtt_msg_base))
    
    def remove_selected_all(self):
        for sc in self.scooter_list:
            if sc is not None:
                sc.selected = 0
        self.last_selected = 0

    #TODO: REPLACE Write this one to replace the random generation in build
    def scooter_arr_add(self, QR_MSG):
        try:
            QR_Content = json.loads(QR_MSG)
            self.center_scooter(QR_Content['name'])
            if self.C_STATE_CTRL[2]:
                if QR_Content['name'] not in self.C_SCOOTER_LIST: 
                    self.C_SCOOTER_LIST.append(QR_Content['name'])
            else:
                self.C_SCOOTER_LIST[0] = QR_Content['name']
        except:
            print("Invalid QR Code")

    def center_scooter(self, qr_msg):
        print(f"Re-centering for {qr_msg}")
        for sc in self.scooter_list:
            if sc != None and qr_msg == sc.marker_id:
                print(f"Pos Update... {sc}")
                self.map_disp.lon=sc.lon
                self.map_disp.lat=sc.lat
                self.map_disp.zoom = 13
        
        
    def create_scooter_marker(self, lat_l, lon_l, scooter_id, scooter_state):
        scooter_marker = AdvMapMarker(lat=lat_l, lon=lon_l, size_hint=(None, None), marker_id=scooter_id, scooter_state=scooter_state)
        scooter_marker.source = 'scooter_marker.PNG'
        scooter_marker.width = 50
        scooter_marker.height = 50
        return scooter_marker

    def create_cg(self, lat_l, lon_l):
        charging_s = MapMarker(lat=lat_l, lon=lon_l, size_hint=(None, None))
        charging_s.source = 'charging_station.PNG'
        charging_s.width = 50
        charging_s.height = 50
        return charging_s

    def camera_update(self, frame):
        ret, frame = self.cam.read()

        if ret:
            grx = self.frame_to_texture(frame)
            self.cam_disp.texture = grx
            qr_objects = decode(frame)

            for o in qr_objects:
                qr_data = o.data.decode('utf-8')
                print(f'QR Code Data: {qr_data}')
                self.QR_MSG = qr_data

    def frame_to_texture(self, frame):
        frame = Camera.cvtColor(frame, Camera.COLOR_BGR2RGB)
        frame = Camera.flip(frame, 0)
        frame = Camera.flip(frame, 1)
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
        texture.blit_buffer(frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        return texture

ScooterAppApp().run()
