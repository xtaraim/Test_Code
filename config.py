'''
Filename: config.py
Description: This module deals with handling parameters stored in the settings.conf file. 
'''

import os
import sys
import glob
import shutil
import ConfigParser
from cStringIO import StringIO

import aes
from password import password as PASSWORD

# Config parse object
config = None

# Base directory
BASE_DIR = None

# Resource directory
RESOURCE_DIR = None

# Running in development or build ('DEV'/'BUILD')
RUN_MODE = None

# The default path for the settings folder
CONFIG_FILE_PATH='/opt/godeep/(encrypted)settings.conf'

def config_init(filepath=CONFIG_FILE_PATH):
    '''Reads the encrypted settings.conf file and decrypts it. Then returns the config object'''
    global config, BASE_DIR
      
    # Get absolute path
    # filepath = BASE_DIR + filepath

    # Read config file
    if not os.path.exists(filepath):
        print '\n\033[91m\033[1mERROR: Config file not found, exiting\033[0m'
        sys.exit(1)
    else:
        print '\nLoading configurations from \033[1m\033[94m%s\033[0m...'%(filepath)

    # Decrypt config data and convert to file like object
    decrypted_file = StringIO(aes.decrypt(filepath, PASSWORD))
    decrypted_file.seek(0)
     
    # Parse config file 
    config = ConfigParser.ConfigParser()
    config.readfp(decrypted_file)
    print '\033[92mDone\n\033[0m'

def get_config(section, item):
    '''Returns the config item'''
    global config
    return config.get(section, item)

def remove_old_temp_folders():
    '''Deletes any old _MEI tmp folders'''
    global RESOURCE_DIR

    print '\nChecking for old temp folders...'
    MEI_folders = glob.glob('/tmp/_MEI*/')

    for MEI in MEI_folders:
        # Skip if it is current sessions tmp folder
        if MEI == RESOURCE_DIR: continue
        # Delete if it is previous sessions tmp folder
        else: 
            print 'Removing temp folder:\033[94m', MEI, '\033[0m'
            shutil.rmtree(MEI)
    
    print '\033[92mDone\n\033[0m'

def set_base_dir(path):
    '''Sets the path to base directory'''
    global BASE_DIR
    BASE_DIR = path + '/'
    print '\n\033[1m>>> Go Deep Base Path: \033[94m%s\033[0m'%(BASE_DIR)

def get_base_dir():
    '''Returns the path to base directory'''
    return BASE_DIR

def set_resource_dir():
    '''Sets the path to resource directory'''
    global RESOURCE_DIR, RUN_MODE

    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        RESOURCE_DIR = sys._MEIPASS + '/'
        RUN_MODE = 'BUILD'
        mode = '\n\033[91m\033[1m*** RUNNING IN BUILD MODE ***\033[0m'

    except Exception as e:
        RESOURCE_DIR = BASE_DIR
        RUN_MODE = 'DEV'
        mode = '\n\033[91m\033[1m*** RUNNING IN DEVELOPMENT MODE ***\033[0m'

    print '\033[1m>>> Go Deep Resources Path: \033[94m%s\033[0m'%(RESOURCE_DIR)
    print mode

    # Remove old tmp folders
    remove_old_temp_folders()
    
def get_resource_dir():
    '''Returns the path to resource directory'''
    return RESOURCE_DIR

def get_mode():
    '''Returns the mode the package is running in (BUILD/DEV)'''
    return RUN_MODE

# Testing
if __name__ == '__main__':
    # Set base and resource paths
    set_base_dir(os.path.dirname(os.path.realpath(__file__)))
    set_resource_dir()

    config_init()
    #print get_config('cctv_camera', 'CCTV_ANALOG')
    print get_config('cctv_camera', 'DEFAULT_CAMERA_USERNAME')
    print get_config('cctv_camera', 'LOW_SENSITIVITY')
    print get_config('auto_testcases','interval_time')
else:
    # Set base and resource paths
    set_base_dir(os.path.dirname(os.path.realpath(__file__)))
    set_resource_dir()

    config_init()
