'''
Filename: CctvCamera.py
Author: Ritwik
Description: This module defines the cctv camera class which encapsulates
all the data specific to a camera and how its video feed can be accesssed

There are additional functions and variables defined which are used by this class.
'''

import cv2
import time
import utils
from utils import logger, bgcolors
from collections import OrderedDict
import datetime
from config import get_config
import threading

# Default Camera credentials
DEFAULT_CAMERA_USERNAME = get_config('cctv_camera', 'DEFAULT_CAMERA_USERNAME')
DEFAULT_CAMERA_PWD = get_config('cctv_camera', 'DEFAULT_CAMERA_PWD')

# Camera Sensitivity
HIGH_SENSITIVITY = int(get_config('cctv_camera', 'HIGH_SENSITIVITY'))
MED_SENSITIVITY = int(get_config('cctv_camera', 'MED_SENSITIVITY'))
LOW_SENSITIVITY = int(get_config('cctv_camera', 'LOW_SENSITIVITY'))

VIDEO_CAP_SLEEP_TIME = int(get_config('cctv_camera', 'VIDEO_CAP_SLEEP_TIME'))

PROCESS_FPS = float(get_config('cctv_camera', 'PROCESS_FPS'))
CAMERA_LOCK = threading.Lock()

def sensitivity_str(sens):
    '''Return sensitivity of camera in string'''
    if sens == HIGH_SENSITIVITY:
        return "High Sensitivity"
    elif sens == MED_SENSITIVITY:
        return "Medium Sensitivity"
    elif sens == LOW_SENSITIVITY:
        return "Low Sensitivity"
    else:
        return "Invalid"

class CctvCamera(object):
    '''A camera object which holds information about the the CCTV camera'''
    camera_count = 0
    analog_count = 1

    def __init__(self, camera_name, email_list, sms_list, call_list, rtsp_url, http_url, floor, favourite,
        object_detect={}, intrusion_start_time=None, intrusion_end_time=None, sound_alarm=False, existing_id=None):

        '''Initializes the camera object class '''
        self.vcap = None
        if existing_id is None:
            self.camera_id = CctvCamera.camera_count
            CctvCamera.camera_count += 1
        
        else:
            self.camera_id = existing_id

        self.fill_cctv_params(camera_name, email_list, sms_list, call_list, rtsp_url, http_url, floor, favourite,
            object_detect, intrusion_start_time, intrusion_end_time, sound_alarm)   

        logger.debug("Creating camera id:%d %s floor:%s favourite:%d with email_list:%s sms_list=%s call_list=%s with rtsp=%s object_detect=%s intrusion_start_time=%s, intrusion_end_time=%s and sound_alarm=%s", self.camera_id, self.camera_name, self.floor, self.favourite, self.email_list, self.sms_list, self.call_list, self.rtsp_url, str(self.object_detect), intrusion_start_time, intrusion_end_time, str(self.sound_alarm))    

    def fill_cctv_params(self, camera_name, email_list, sms_list, call_list, rtsp_url, http_url, floor, favourite,
        object_detect, intrusion_start_time, intrusion_end_time, sound_alarm):
        '''Populates the camera parameters'''

        self.camera_name = camera_name
        self.rtsp_url = rtsp_url
        self.http_url = http_url
        self.floor = floor
        self.favourite = favourite

        self.email_list = list(set(email_list))
        if '' in self.email_list:
            self.email_list.remove('')
        self.sms_list = list(set(sms_list))
        if '' in self.sms_list:
            self.sms_list.remove('')
        self.call_list = list(set(call_list))
        if '' in self.call_list:
            self.call_list.remove('')

        self.intrusion_start_time = intrusion_start_time
        self.intrusion_end_time = intrusion_end_time
        self.object_detect = object_detect
        self.sound_alarm = sound_alarm

    def edit_cctv_params(self, camera_name, email_list, sms_list, call_list, rtsp_url, http_url, floor, favourite,
        object_detect, intrusion_start_time, intrusion_end_time, sound_alarm):

        '''Edit the CCTV parameters'''
        self.fill_cctv_params(camera_name, email_list, sms_list, call_list, rtsp_url, http_url, floor, favourite,
            object_detect, intrusion_start_time, intrusion_end_time, sound_alarm)

        logger.debug("Editing camera id:%d %s floor:%s favourite:%d with email_list:%s sms_list=%s call_list=%s with rtsp=%s object_detect=%s intrusion_start_time=%s, intrusion_end_time=%s and sound_alarm=%s", self.camera_id, self.camera_name, self.floor, self.favourite, self.email_list, self.sms_list, self.call_list, self.rtsp_url, str(self.object_detect), intrusion_start_time, intrusion_end_time, str(self.sound_alarm)) 

    def get_video_cap(self):
        '''Return the appropriate video capture object or None if no such object found '''
        logger.debug("Attempting to access camera via RTSP URL: %s"%(self.rtsp_url))

        CAMERA_LOCK.acquire()
        print 'VideoCapture lock acquire:', self.camera_name

        print 'Waiting for %ds'%VIDEO_CAP_SLEEP_TIME, self.camera_name
        time.sleep(VIDEO_CAP_SLEEP_TIME)
        
        try:
            if self.vcap != None:
                print 'VCAP object already exists, destroying first', self.camera_name
                self.vcap.release()

            self.vcap = cv2.VideoCapture(self.rtsp_url)
            print 'VideoCapture success:', self.camera_name

        except Exception as ex:
            print 'VideoCapture failed:', self.camera_name
            logger.error(ex.message)

        print 'VideoCapture lock release:', self.camera_name
        CAMERA_LOCK.release()

        return self.vcap

    def get_frame_rate(self):
        '''Return the expected number of frames to be processed per second based on the camera sensitivity setting'''
        # As of now, we are only supporting 1 frame for every 2 seconds. Therefore, the sensiitivity setting
        # doesn't matter
        fr = PROCESS_FPS
        # if self.camera_sensitive == HIGH_SENSITIVITY:
        #     fr = 3
        # elif self.camera_sensitive == MED_SENSITIVITY:
        #     fr = 2
        # else:
        #     fr = 0.5
        return fr

    def get_camera_info(self):
        '''Return camera info in dicitonary format'''
        return_dict = OrderedDict()
        return_dict["camera_name"] = self.camera_name
        return_dict["email_list"] = self.email_list
        return_dict["sms_list"] = self.sms_list
        return_dict["call_list"] = self.call_list
        return_dict["rtsp_url"] = self.rtsp_url
        return_dict["http_url"] = self.http_url
        return_dict["floor"] = self.floor
        return_dict["favourite"] = self.favourite
        return_dict["object_detect"] = self.object_detect
        return_dict["intrusion_start_time"] = self.intrusion_start_time
        return_dict["intrusion_end_time"] =  self.intrusion_end_time
        return_dict["sound_alarm"] = self.sound_alarm

        return return_dict

    def is_intrusion_enabled(self):
        '''Check whether intrusion is enabled at this instant in time'''
        ret = False
        if self.object_detect["intrusion"] == 1:
            current_time = datetime.datetime.now().time()
            start_time = datetime.time(int(self.intrusion_start_time.split(':')[0]), int(self.intrusion_start_time.split(':')[1]))
            end_time = datetime.time(int(self.intrusion_end_time.split(':')[0]), int(self.intrusion_end_time.split(':')[1]))

            if start_time < end_time and start_time < current_time and current_time < end_time:
                ret = True
            if start_time > end_time and (current_time > start_time or current_time < end_time):
                ret = True

        return ret
