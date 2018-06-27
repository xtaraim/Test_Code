'''Filename - utils.py
Description - This module handles the auxillary requirements such as getting thread id and creating logger file.
'''
import os
import Queue
import ctypes
import datetime
import threading
import logging
import logging.handlers
import cv2
import time
from config import get_config, get_base_dir

# Logging
LOG_FOLDER = get_base_dir() + get_config('utils', 'LOG_FOLDER')
LOG_FILE = get_base_dir() + get_config('utils', 'LOG_FILE')
TEMP_FOLDER = get_base_dir() + get_config('camera_controller', 'TEMP_FOLDER')
MAX_EMAIL_Q_SZ = int(get_config('utils', 'MAX_EMAIL_Q_SZ'))
MAX_SMS_Q_SZ = int(get_config('utils', 'MAX_SMS_Q_SZ'))
MAX_CALL_Q_SZ = int(get_config('utils', 'MAX_CALL_Q_SZ'))
Q_ITEM_WAIT_TIME = int(get_config('utils', 'Q_ITEM_WAIT_TIME'))

# Threading related
libc = ctypes.cdll.LoadLibrary('libc.so.6')

# System dependent, see e.g. /usr/include/x86_64-linux-gnu/asm/unistd_64.h
SYS_gettid = 186

# Queues
call_q = Queue.Queue(maxsize=MAX_CALL_Q_SZ)
sms_q = Queue.Queue(maxsize=MAX_SMS_Q_SZ)
email_q = Queue.Queue(maxsize=MAX_EMAIL_Q_SZ)

DetectedObjects = {}
DetectedObj_lock = threading.Lock()

# Flags
YOLO_READY_FLAG = False
YOLO_READY_LOCK = threading.Lock()

def set_yolo_flag(val):
    global YOLO_READY_FLAG, YOLO_READY_LOCK
    YOLO_READY_LOCK.acquire()
    YOLO_READY_FLAG = val
    YOLO_READY_LOCK.release()

def get_yolo_flag():
    global YOLO_READY_FLAG
    return YOLO_READY_FLAG

def notify_detection(image, camera_id, camera_name, email_list, sms_list, call_list, obj, prediction_val):
    '''Generate alerts and notify of detected object'''
    global DetectedObjects
    current_time = datetime.datetime.now().isoformat(' ')
    image_name = os.path.join(TEMP_FOLDER, camera_name + current_time + ".jpg")

    logger.debug("Saving Image %s for cam:%s at %s and generating alerts..."%(image_name, camera_name, current_time))
    cv2.imwrite(image_name, image)

    try:
        print 'Queue <--', camera_name, current_time
        
        if email_list: 
            email_q.put((email_list, obj, current_time, camera_name, prediction_val, image_name))

        if sms_list:
            sms_q.put((sms_list, obj, current_time, camera_name, prediction_val))

        if call_list:
            call_q.put((call_list, obj))

    except Queue.Full as ex:
        logger.error("Queue is full! " + str(ex))
        print 'Queue is full'

    # Add detected object to list of detected objects
    with DetectedObj_lock:
        if camera_id not in DetectedObjects:
            DetectedObjects[camera_id] = list()
        
        DetectedObjects[camera_id].append(obj)
   
        # Ensure that entries are unique
        DetectedObjects[camera_id] = list(set(DetectedObjects[camera_id]))

def return_alert_info():
    with DetectedObj_lock:
        global DetectedObjects
        ret = dict(DetectedObjects)
        DetectedObjects.clear()
        return ret
    
class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, target=None, args=None, name=None, daemon=True):
        if args:
            super(StoppableThread, self).__init__(target=target, args=args, name=name)
        else:
            super(StoppableThread, self).__init__(target=target, name=name)

        self.daemon = daemon
        self._stop_event = threading.Event()
        self.name = name

    def stop(self):
        print '\n%sStop requested for %s%s'%(bgcolors.WARNING, self.name, bgcolors.ENDC)
        self._stop_event.set()

    def join(self, timeout=10):
        print '\n%sJoin requested for %s%s'%(bgcolors.WARNING, self.name, bgcolors.ENDC)
        self._stop_event.set()
        threading.Thread.join(self, timeout)

    def stopped(self):
        return self._stop_event.is_set()

def timeout(func, args=(), kwargs={}, timeout_duration=Q_ITEM_WAIT_TIME, default=None):
    import threading
    class InterruptableThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = None

        def run(self):
            try:
                self.result = func(*args, **kwargs)
            except:
                self.result = default

    it = InterruptableThread()
    it.start()
    it.join(timeout_duration)
    if it.isAlive():
        return default
    else:
        return it.result

class bgcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_tid():
    """Returns OS thread id - Specific to Linux"""
    return libc.syscall(SYS_gettid)

def display_tid(tname, tid):
    '''Displays the name and the thread id'''
    print bgcolors.FAIL + 'Name: %s, TID:%s %d\n'%(tname, bgcolors.ENDC, tid)

def get_logger():
    '''Checks and if not present, creates a log folder and a log file in it'''
    if not os.path.exists(LOG_FOLDER):
        print 'Creating log folder at %s%s%s...'%(bgcolors.BOLD + bgcolors.OKBLUE, LOG_FOLDER, bgcolors.ENDC)
        os.makedirs(LOG_FOLDER)
        print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

    if not os.path.exists(LOG_FILE):
        print 'Creating %s%s%s...'%(bgcolors.BOLD + bgcolors.OKBLUE, LOG_FILE, bgcolors.ENDC)
        os.mknod(LOG_FILE)
        print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC   

    fmt = logging.Formatter('%(asctime)s [%(filename)s:%(lineno)s - %(funcName)s]%(levelname)s : {PID:%(process)d}: %(message)s',\
    datefmt='%m/%d/%Y %I:%M:%S %p')

    my_handler = logging.handlers.RotatingFileHandler(LOG_FILE, mode='a', maxBytes=5*1024*1024, backupCount=10, encoding=None, delay=0)
    my_handler.setFormatter(fmt)
    my_handler.setLevel(logging.NOTSET)
    app_log = logging.getLogger()
    app_log.setLevel(logging.NOTSET)
    app_log.addHandler(my_handler)

    return app_log

logger = get_logger()
