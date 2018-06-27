'''
Filename: auto_notifier.py
Description: This module is scheduled by the crontab to be executed in every 1 minute. This, in turn
checks if the http_handler is being executed or not. And if it is not, it is being called.
'''

import os
import time
import subprocess

SOURCE_CODE = False

CODE_DIR = '/home/' + os.path.expanduser('~') + '/POC'
BIN_DIR = '/opt/godeep'
MAIN_FILE = 'GoDeep'

CHECK_INTERVAL = 20

def start_backend():
    start_time = time.time()

    if SOURCE_CODE: exec_file = os.path.join(CODE_DIR, MAIN_FILE)
    else: exec_file = os.path.join(BIN_DIR, MAIN_FILE)

    while (time.time() - start_time < 59):        
        p = subprocess.Popen(['pgrep', '-f', MAIN_FILE], stdout=subprocess.PIPE)
        out, err = p.communicate()

        if len(out.strip()) == 0:
            cmd = "%s"%(exec_file)
            p1 = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
            out, err = p1.communicate()
            
            time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    start_backend()
