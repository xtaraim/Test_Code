'''
Filename: http_handler.py
Description: This is the server and handles all the request from the frontend.
'''
import os
import sys
import json
import time
import signal

import SocketServer
from BaseHTTPServer import BaseHTTPRequestHandler

import config
import run_testcases

# Set base directory
config.set_base_dir(os.path.dirname(os.path.realpath(__file__)))

# Set resource directory
config.set_resource_dir()

# Initialize configurations
config.config_init()

import camera_controller
from utils import StoppableThread, bgcolors, set_yolo_flag, get_yolo_flag
from camera_database import CameraDatabase
import licensing
from auto_notifier import start_monitor_thread, stop_monitor_thread
import performance

os.environ['TF_CPP_MIN_LOG_LEVEL'] = config.get_config('http_handler', 'TF_LOG_LEVEL')
DEFAULT_IP = config.get_config('http_handler', 'DEFAULT_IP')
DEFAULT_PORT = int(config.get_config('http_handler', 'DEFAULT_PORT'))

# Background image
Current_Background = {}
print 'Initializing background database...'
BCG_DB = CameraDatabase('backgroundDB', 'background')
print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

# Licensing message
LICENSE_MSG = None

httpd = None

def signal_handler(signal, frame):
    performance.deinitialize_performance()
    deinitialize_backend()
    httpd.server_close()
    print bgcolors.FAIL + bgcolors.BOLD + '\nExiting Main' + bgcolors.ENDC
    sys.exit(0)

class MyHandler(BaseHTTPRequestHandler):

    def send_response_data(self, data):
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            json_data = json.dumps(data)
            self.wfile.write(json_data)
            self.wfile.close()
            print("\nSending response body: \n%s"%(json_data))
        except Exception as ex:
            print bgcolors.FAIL + bgcolors.BOLD + ex.message + bgcolors.ENDC
            self.send_response(400)

    def do_GET(self):
        '''This function handles the GET requests made by the frontend'''
        if self.path == "/getLicense":
            print bgcolors.WARNING + "\nReceived get license details request\n" + bgcolors.ENDC
            data = licensing.get_license_details()
            self.send_response_data(data)
            return

        # Block all requests if license is not valid
        print 'Call from GET method'
        ret, msg = licensing.is_license_valid()
        if not ret:
            deinitialize_backend()
            return_dict = {"status": ret, "reason": msg}
            self.send_response_data(return_dict)
            return

        if self.path == "/getAllCameraInfo":
            data = camera_controller.get_all_camera_info()
            self.send_response_data(data)

        elif "/getCameraInfo/" in self.path:
            try:
                camera_id = int(self.path.split('/')[-1])
                data = camera_controller.get_camera_info(camera_id)
                self.send_response_data(data)
            except Exception as ex:
                self.send_response(400)
                self.send_header('Content-Type', 'text')
                self.end_headers()
                self.wfile.write(ex.message)
                self.wfile.close()

        elif self.path == "/alertInfo":
            data = camera_controller.get_alert_info()
            self.send_response_data(data)

        # TODO: Remove this method??
        elif "/getFrame/" in self.path:
            try:
                print bgcolors.WARNING + bgcolors.BOLD + "\nGet frame request" + bgcolors.ENDC
                camera_id = int(self.path.split('/')[-1])
                data = camera_controller.get_frame(camera_id)
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.end_headers()
                self.wfile.write(data)
                self.wfile.close()
            except Exception as ex:
                self.send_response(400)
                self.send_header('Content-Type', 'text')
                self.end_headers()
                self.wfile.write(ex.message)
                self.wfile.close()

        elif "/getBackground" in self.path:
            try:
                self.send_response_data(Current_Background)
            except Exception as ex:
                self.send_response(400)
                self.send_header('Content-Type', 'text')
                self.end_headers()
                self.wfile.write(ex.message)
                self.wfile.close()

        else:
            self.send_response(200)

    def do_POST(self):
        '''This function handles the GET requests made by the frontend'''
        if self.path == "/licenseUpdate":
            print bgcolors.WARNING + "\nReceived update license request\n" + bgcolors.ENDC
            try:
                ret, msg = licensing.update_license()
                if ret:
                    initialize_backend()
                    return_dict = {"status": ret, "reason": msg}
                    self.send_response_data(return_dict)
                else:
                    deinitialize_backend()
                    return_dict = {"status": ret, "reason": msg}
                    self.send_response_data(return_dict)

            except Exception as ex:
                self.send_response(400)
                self.send_header('Content-Type', 'text')
                self.end_headers()
                # TODO: Dont send backend messages to frontend
                self.wfile.write(ex.message)
                self.wfile.close()
            return
    
        # Block all requests if license is not valid
        print 'Call from POST method'
        ret, msg = licensing.is_license_valid()
        if not ret:
            deinitialize_backend()
            return_dict = {"status": ret, "reason": msg}
            self.send_response_data(return_dict)
            return

        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        
        if self.path == '/createCamera':
            try:
                print bgcolors.WARNING + "\nReceived Create Camera Request with info:\n%s"%(post_body) + bgcolors.ENDC
                data = camera_controller.create_camera(post_body)
                self.send_response_data(data)
            except Exception as ex:
                self.send_response(400)
                self.send_header('Content-Type', 'text')
                self.end_headers()
                self.wfile.write(ex.message)
                self.wfile.close()

        elif "/editCamera/" in self.path:
            try:
                print bgcolors.WARNING + "\nReceived Edit Camera Request with info:\n%s"%(post_body) + bgcolors.ENDC
                camera_id = int(self.path.split('/')[-1])
                data = camera_controller.edit_camera(camera_id, post_body)
                self.send_response_data(data)
            except Exception as ex:
                self.send_response(400)
                self.send_header('Content-Type', 'text')
                self.end_headers()
                self.wfile.write(ex.message)
                self.wfile.close()

        elif "/deleteCamera/" in self.path:
            try:
                camera_id = int(self.path.split('/')[-1])
                print bgcolors.WARNING + bgcolors.BOLD + "\nReceived Delete Camera Request for camera: %d"%(camera_id) + bgcolors.ENDC
                data = camera_controller.delete_camera(camera_id)
                self.send_response_data(data)
            except Exception as ex:
                self.send_response(400)
                self.send_header('Content-Type', 'text')
                self.end_headers()
                self.wfile.write(ex.message)
                self.wfile.close()

        elif "/sendBackground" in self.path:
            try:
                input_dict = json.loads(post_body)
                Current_Background["image"] = input_dict["image"]

                # Save background info in database
                if BCG_DB.get_max_id() is None: BCG_DB.insert(0, input_dict)
                else: BCG_DB.edit(0, input_dict)

                data = {"status": True}
                self.send_response_data(data)
            except Exception as ex:
                self.send_response(400)
                self.send_header('Content-Type', 'text')
                self.end_headers()
                self.wfile.write(ex.message)
                self.wfile.close()
    
        else:
            self.send_response(200)


def initialize_backend():
    ''' First try to close any ongoing backend sessions and initialize a fresh backend'''
    deinitialize_backend()

    print bgcolors.WARNING + '\nInitialize Backend' + bgcolors.ENDC

    # Now restart backend sessions
    licensing.start_license_thread()
    camera_controller.initialize_model()
    
    # Wait till YOLO is ready
    while not get_yolo_flag():
        print "YOLO Status:", get_yolo_flag()
        time.sleep(1)
    print bgcolors.OKGREEN + 'YOLO Graph Loaded' + bgcolors.ENDC 

    camera_controller.initialize_database()

    # Notification thread
    start_monitor_thread()

def deinitialize_backend():
    print bgcolors.WARNING + '\nDeinitialize Backend' + bgcolors.ENDC

    # Close backend sessions
    licensing.stop_license_thread()
    camera_controller.delete_all_cameras(delete_from_db=False)
    camera_controller.deinitialize_model()
    set_yolo_flag(False)

    # Stop notifictaion thread handler
    stop_monitor_thread()

if __name__ == '__main__':

    signal.signal(signal.SIGINT, signal_handler)

    # Start performance monitor thread
    performance.initialize_performance()
    
    # Background image
    if BCG_DB.get_max_id() is not None:
        bcg_image = BCG_DB.retrieve(0)[0][1]['image']
        print 'Updating background image with ' + bgcolors.WARNING + bcg_image + bgcolors.ENDC
        Current_Background['image'] = bcg_image
        print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

    # Licensing
    licensing.initialize_licensing()
    ret, LICENSE_MSG = licensing.update_license()

    # If valid license found, initialize backend
    if ret: initialize_backend()
    else: deinitialize_backend()
    print 'Licensing Status: %s%s%s\n'%(bgcolors.OKBLUE, LICENSE_MSG, bgcolors.ENDC)

    # Display backend status 
    time.sleep(2)
    run_testcases.display()
    print bgcolors.FAIL + bgcolors.BOLD + '\nGoDeep PID: %s%d'%(bgcolors.ENDC, os.getpid())
    print bgcolors.OKGREEN + bgcolors.BOLD + 'Backend Setup Complete' + bgcolors.ENDC
    print 'GoDeep Home Page, visit ' + bgcolors.UNDERLINE + bgcolors.OKBLUE + bgcolors.BOLD + 'http://localhost/godeep' + bgcolors.ENDC
    print 'To add cameras, visit ' + bgcolors.UNDERLINE + bgcolors.OKBLUE + bgcolors.BOLD + 'http://localhost/godeep/add' + bgcolors.ENDC
    print 'To view cameras, visit ' + bgcolors.UNDERLINE + bgcolors.OKBLUE + bgcolors.BOLD + 'http://localhost/godeep/view\n' + bgcolors.ENDC

    # HTTP server setup
    SocketServer.TCPServer.allow_reuse_address = True
    httpd = SocketServer.TCPServer((DEFAULT_IP, DEFAULT_PORT), MyHandler)
    httpd.serve_forever()
