from server_stm import create_server_manager
from flask import Flask, render_template, request, jsonify
import os
import time
import subprocess

NUMBER_OF_SCOOTERS = 5


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
    
    
    app = Flask(__name__, static_folder='uimages')

    # state machine connected to this server
    server_manager_instance  = create_server_manager(NUMBER_OF_SCOOTERS)
    
    # other state machines need to spawn as independent processes
    scooter_process = subprocess.Popen(['python3', 'scooter_stm_spawner.py', str(NUMBER_OF_SCOOTERS)])
    
    
    @app.route('/')
    def index():
        # html files needs to be placed in a folder called "templates", Flask looks there by default to find the requested template
        return render_template('system_manager_app.html')

    # generate_heatmap() function receives the "button click" event
    # from html template to trigger server-stm transition
    # which facilitates collection of scooter positional data
    @app.route('/generate_heatmap', methods=['POST'])
    def generate_heatmap():
        event = request.form.get('event')
        if event == 'button_clicked':
            if os.path.exists('uimages/scooter_plot.png'):
                os.remove('uimages/scooter_plot.png')
                print('FLASK: Removed existing scooter_plot.png')
            server_manager_instance.stm_driver.send('get_positional_data', 'my_server')
            picture_found = False
            while not picture_found:
                picture_found = os.path.exists('uimages/scooter_plot.png')
            return jsonify({'status': 'success', 'triggered': event})
        else:
            return jsonify({'status': 'error', 'message': f'Invalid event: {event}'}), 400

    @app.route('/generate_scooter_stats', methods=['POST'])
    def generate_scooter_stats():
        event = request.form.get('event')
        if event == 'button_clicked':
            # You can interact with the scooter_manager_instance here if needed
            # scooter_names = scooter_manager_instance.scooters
            return jsonify({'status': 'success', 'triggered': event, 'scooter_stats': list(server_manager_instance.scooter_stats.items())})
        else:
            return jsonify({'status': 'error', 'message': f'Invalid event: {event}'}), 400
    
    @app.route('/stop_everything', methods=['POST'])
    def stop_everything():
        event = request.form.get('event')
        if event == 'button_clicked':
            server_manager_instance.stm_driver.send('abort', 'my_server')
            # schedule server shutdown after 10 seconds
            flask_server_shutdown(scooter_process)
            
        else:
            return jsonify({'status': 'error', 'message': f'Invalid event: {event}'}), 400
        
    app.run(use_reloader=False)

    
    
    
    