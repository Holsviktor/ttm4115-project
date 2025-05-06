from server_stm import create_server_manager
from flask import Flask, render_template, request, jsonify
import os
import time
import subprocess

NUMBER_OF_SCOOTERS = 10

def flask_server_shutdown(scooter_process):
        time.sleep(5)
        print("Flask server says: shutting down scooter stm process.")
        if scooter_process.poll() is None: 
            scooter_process.terminate()     
            try:
                scooter_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                scooter_process.kill()   
          
        print("Countdown to Flask server shutdown: ")
        for i in range(1, 11):
            print(f"{11 - i} . . .")
            time.sleep(0.2)
        print("Flask server says: GOODBYE!")
        os._exit(0) 
        

if __name__ == '__main__':
    
    app = Flask(__name__, static_folder='images')

    # state machine connected to this server
    server_manager_instance  = create_server_manager(NUMBER_OF_SCOOTERS)
    
    # other state machines need to spawn as independent processes
    scooter_process = subprocess.Popen(['python3', 'scooter_stm_spawner.py', str(NUMBER_OF_SCOOTERS)])
    
    # charger process should run in the separate raspberry pi, since it needs motion sensor
    # charger_process = subprocess.Popen(['python3', 'charger_stm.py'])
    
    
    @app.route('/')
    def index():
        # html files needs to be placed in a folder called "templates", Flask looks there by default to find the requested template
        return render_template('system_manager_app.html')

    @app.route('/generate_heatmap', methods=['POST'])
    def generate_heatmap():
        event = request.form.get('event')
        if event == 'button_clicked':
            if os.path.exists('images/scooter_plot.png'):
                os.remove('images/scooter_plot.png')
                print('FLASK: Removed existing scooter_plot.png')
            server_manager_instance.stm_driver.send('get_positional_data', server_manager_instance.name)
            picture_found = False
            while not picture_found:
                picture_found = os.path.exists('images/scooter_plot.png')
            return jsonify({'status': 'success', 'triggered': event})
        else:
            return jsonify({'status': 'error', 'message': f'Invalid event: {event}'}), 400

    @app.route('/generate_scooter_stats', methods=['POST'])
    def generate_scooter_stats():
        event = request.form.get('event')
        if event == 'button_clicked':
            return jsonify({'status': 'success', 'triggered': event, 'scooter_stats': list(server_manager_instance.scooter_stats.items())})
        else:
            return jsonify({'status': 'error', 'message': f'Invalid event: {event}'}), 400
        
    @app.route('/generate_previous_bookings', methods=['POST'])
    def generate_previous_bookings():
        event = request.form.get('event')
        if event == 'button_clicked':
            return jsonify({'status': 'success', 'triggered': event, 'past_bookings': list(server_manager_instance.past_bookings.items())})
        else:
            return jsonify({'status': 'error', 'message': f'Invalid event: {event}'}), 400
    
    @app.route('/stop_everything', methods=['POST'])
    def stop_everything():
        event = request.form.get('event')
        if event == 'button_clicked':
            server_manager_instance.stm_driver.send('abort', server_manager_instance.name)
            flask_server_shutdown(scooter_process)
        else:
            return jsonify({'status': 'error', 'message': f'Invalid event: {event}'}), 400
        
    app.run(use_reloader=False)

    
    
    
    