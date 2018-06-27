'''Filename: licensing.py
Description: This module handles the licensing of the software. It reads a license file,
makes sure that the license was valid for the system and check if the validity of the license 
depending on the usage of the software.
'''
import os.path
import time
import json
import threading
from aes import decrypt
from subprocess import Popen, PIPE, check_output

import config
import camera_controller
from camera_database import CameraDatabase
from utils import logger, bgcolors, StoppableThread, get_tid
import performance
import auto_testcases
# TODO: Replace with config
UPDATE_INTERVAL = int(config.get_config('licensing', 'UPDATE_INTERVAL'))

USAGE_LOCK = threading.Lock()
LICENSE_THREAD = None

LICENSE_FILE = config.get_config('licensing', 'LICENSE_FILE')
ENCRYPT_PASS = config.get_config('licensing', 'ENCRYPT_PASS')
LICENSE_DB = None
LICENSE_PARAMS = {
    "validity": 0,
    "used": 0, 
    "uuid": None,
    "license_id": None
    }

def initialize_licensing():
    '''Setup the the licening DB and add entry to it '''
    global LICENSE_DB
    LICENSE_DB = CameraDatabase('licenseDB', 'time_elapsed')

def read_license_file():
    '''This module reads a encrypted license file, decrypts it and reads the data 
    into the dictionary LICENSE_PARAMS'''
    global LICENSE_PARAMS

    # print bgcolors.WARNING + '\nRead license file' + bgcolors.ENDC

    if not os.path.isfile(LICENSE_FILE):
        logger.info('License file does not exists')
        return (False, 'License file not found')

    # Decrypt license file
    decrypted = decrypt(LICENSE_FILE, ENCRYPT_PASS)
    try:
        license_dict = json.loads(decrypted)
    except Exception as e:
        return (False, 'License file is corrupted')

    # print 'License file data:', license_dict

    # Update license dict with latest license params
    LICENSE_PARAMS['validity'] = license_dict['validity']
    LICENSE_PARAMS['uuid'] = license_dict['uuid']
    LICENSE_PARAMS['license_id'] = license_dict['license_id']

    return (True, 'Success')

def get_uuid():
    '''This module gets the UUID of the system'''
    # print bgcolors.WARNING + '\nGet System UUID' + bgcolors.ENDC

    fails = 0

    while True:
        time.sleep(0.5)
        try:
            cmd = 'lshal | grep -i system.hardware.uuid'
            term = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
            stdout, stderr = term.communicate()

            # Command executed successfully
            if term.returncode == 0:
                uuid = stdout.split('\'')[1]
                break

            else:
                fails += 1
                print bgcolors.FAIL + 'UUID access failed: %d'%(fails) + bgcolors.ENDC

        except Exception as e:
            print e

    # print 'System UUID:', uuid
    return uuid

def is_license_valid():
    '''Read the license file and check if it valid and return the response'''
    global LICENSE_PARAMS
    uuid_valid = False
    uuid = None

    # print bgcolors.WARNING + '\nVerifying license ID' + bgcolors.ENDC

    # Update license dict
    ret, msg = read_license_file()
    if not ret:
        return (False, msg)

    try:        
        # Verify the Product ID
        uuid = get_uuid()        

        if uuid == LICENSE_PARAMS['uuid']:
            uuid_valid = True
        else: 
            return (False, 'License is not valid for this system')

        # Verify if the time validity has not expired
        USAGE_LOCK.acquire()
        usage_in_hr = LICENSE_PARAMS['used']
        USAGE_LOCK.release()

        print 'Usage in hour: %d' %(usage_in_hr)
        
        if uuid_valid and ((usage_in_hr) < (LICENSE_PARAMS['validity'])):
            return (True, 'Success')
        else:
            return (False, 'This license has expired')

    except Exception as ex:
        print ex
        logger.error(ex.message)

    return (False, 'Failed')

def update_license():
    '''Every UPDATE_INTERVAL, update for how long the backend has been running'''
    global LICENSE_PARAMS

    # print bgcolors.WARNING + '\nRetrieving license from database' + bgcolors.ENDC

    # Update license dict
    ret, msg = read_license_file()
    if not ret:
        return (False, msg)

    # If license exists check validity
    retrieve_data = LICENSE_DB.retrieve(LICENSE_PARAMS['license_id'])
    
    if not retrieve_data:
        # If license file exists but not added in database, try to add it
        return add_license()

    else:
        USAGE_LOCK.acquire()
        LICENSE_PARAMS['used'] = retrieve_data[0][1]
        USAGE_LOCK.release()
        return is_license_valid()

def add_license():
    '''Adds a license file'''
    
    global LICENSE_PARAMS

    # print bgcolors.WARNING + '\nAdding license to database' + bgcolors.ENDC

    # Update license dict
    ret, msg = read_license_file()
    if not ret:
        return (False, msg)

    ret = LICENSE_DB.insert(LICENSE_PARAMS['license_id'], 0)
    if ret:
        # Reset used time to 0 for new license
        USAGE_LOCK.acquire()
        LICENSE_PARAMS['used'] = 0
        USAGE_LOCK.release()
        return (True, 'Success')
    else:
        return (False, 'Could not add the license')

def get_license_details():
    print bgcolors.WARNING + '\nGet license details' + bgcolors.ENDC

    ret, msg = is_license_valid()

    if ret:
        USAGE_LOCK.acquire()
        return_dict = {
            'status': ret,
            'reason': msg,
            'validity': LICENSE_PARAMS['validity'],
            'used': LICENSE_PARAMS['used']
        }
        USAGE_LOCK.release()

    else:
        return_dict = {
            'status': ret,
            'used': LICENSE_PARAMS['used'],
            'validity': LICENSE_PARAMS['validity'],
            'reason': msg
        }

    return return_dict

def update_usage():
    '''Every UPDATE_INTERVAL, update for how long the backend has been running'''
    global LICENSE_PARAMS
    count = 1

    t = threading.currentThread()
    performance.add_thread()
    print bgcolors.FAIL + 'Update license usage TID: %d\n'%(get_tid()) + bgcolors.ENDC
    
    # Keep running detection thread as long as stop event not occurred
    while (not t.stopped()):

        # TODO: Revise this if statement below
        if count % UPDATE_INTERVAL == 0:

            print bgcolors.WARNING + '\nUpdate usage' + bgcolors.ENDC
            
            try: 
                # Get current usage from database
                usage_in_hr = LICENSE_DB.retrieve(LICENSE_PARAMS['license_id'])[0][1]
                usage_in_hr += 1
                LICENSE_DB.edit(LICENSE_PARAMS['license_id'], usage_in_hr)

                print "Usage in hours: %d" %(usage_in_hr)
                
                USAGE_LOCK.acquire()
                LICENSE_PARAMS['used'] = usage_in_hr
                USAGE_LOCK.release()

                ret, msg = is_license_valid()
                # Stop thread after license expires
                if not ret:
                    print 'From while loop:', msg
                    auto_testcases.update_license_logfile()
                    t.stop()
                    break
        
            except Exception as ex:
                print ex
                logger.error(ex.message)
               
        time.sleep(1)
        count += 1

    # Deinit backend sessions
    print bgcolors.FAIL + 'Clean up from license thread' + bgcolors.ENDC
    camera_controller.delete_all_cameras(delete_from_db=False)
    camera_controller.deinitialize_model()

def start_license_thread():
    global LICENSE_THREAD

    print bgcolors.OKBLUE + '\nStarting license update thread' + bgcolors.ENDC
    try:
        # TODO: Args need to removed
        LICENSE_THREAD = StoppableThread(target=update_usage, name='License-Thread')
        LICENSE_THREAD.start()
        print bgcolors.OKGREEN + 'Start Done\n' + bgcolors.ENDC
        
    except Exception as e:
        print e 

def stop_license_thread():
    global LICENSE_THREAD

    print bgcolors.OKBLUE + '\nStopping license update thread' + bgcolors.ENDC
    try:
        if LICENSE_THREAD.is_alive():
            LICENSE_THREAD.join()
            LICENSE_THREAD = None
            print bgcolors.OKGREEN + 'Stop Done\n' + bgcolors.ENDC

    except Exception as e: 
        print e
get_license_details()