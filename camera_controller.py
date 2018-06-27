'''
Filename: camera_controller.py
Description: This module defines the functions which handles the working of the 
cameras such as create, delete and edit camera database. It also defines the function 
that detects the object.

There are additional functions and variables defined which are used by these functions.
'''

import json, datetime, cv2
import threading
import operator
import time
import os
import Queue
import cctv_camera, auto_notifier, utils
from utils import *
from camera_database import CameraDatabase
from config import get_config, get_base_dir
from darknet import darknet
import performance


# Cameras that are actively working right now
ActiveCameras = {}

# Digital Camera database object
cdb = None
DETECTION_STATUS_ON = 1

DETECTION_THRESHOLD = int(get_config('camera_controller', 'DETECTION_THRESHOLD'))
MIN_DETECT_INTERVAL = int(get_config('camera_controller', 'MIN_DETECT_INTERVAL'))
MAX_Q_SZ = int(get_config('camera_controller', 'MAX_DETECTION_Q_SIZE'))
MIN_HEIGHT_DIM = int(get_config('camera_controller', 'MIN_HEIGHT_DIM'))
TEMP_FOLDER = get_base_dir() + get_config('camera_controller', 'TEMP_FOLDER')

# Performance Testing
AVERAGE_FPS = None
AVERAGE_SUM = 0.0
AVERAGE_COUNT = 0.0

yolo_q = Queue.Queue(maxsize=MAX_Q_SZ)
yolo_p = None

def initialize_database():
    '''
    It creates an object for camera database and retrieves camera info from existing 
    database and update the ActiveCameras dictionary. 
    Also, it updates camera count and takes care of ID for new camera
    '''
    global cdb
    
    print 'Initializing camera database...'

    # Create camera database object
    cdb = CameraDatabase('camDB', 'camTable')

    # Update camera count
    cdb_latest_id = cdb.get_max_id()
    if cdb_latest_id is not None:
        # Retrieve info from database and update the ActiveCameras dictionary
        update_ActiveCameras()

        # Increment camera count by 1 to assign new ID for new camera
        cctv_camera.CctvCamera.camera_count = cdb_latest_id + 1

    print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

def update_ActiveCameras():
    global cdb

    # Retrieve all info from camera database
    camera_infos = cdb.retrieve()
    print 'Retrieved %s%d%s camera(s) from database'%(bgcolors.WARNING, len(camera_infos), bgcolors.ENDC)
    for cam_id, cam_dict in camera_infos:
        create_camera(cam_dict, existing_id=cam_id, input_is_JSON=False)

def initialize_model():
    global yolo_p
    print 'Initializing models...'
    
    yolo_p = StoppableThread(target=darknet.load_yolo, args=(yolo_q,), name="YOLO Thread")
    yolo_p.start()
    
    performance.add_detect_q(yolo_q)
    print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

    if not os.path.exists(TEMP_FOLDER):
        print 'Creating temp folder at %s%s%s...'%(bgcolors.BOLD + bgcolors.OKBLUE, TEMP_FOLDER, bgcolors.ENDC)
        os.makedirs(TEMP_FOLDER)
        print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

def deinitialize_model():
    if yolo_p:
        yolo_p.join()
    print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

def create_camera(input_data, existing_id=None, input_is_JSON=True):
    '''Create a camera object afer taking input JSON format. Return true if 
    the camera object is created successfully else return false
    Add the camera object to ActiveCameras dictionary.
    Add the camera info into camera database if it does not exists'''
    return_dict = {"status":False}

    if input_is_JSON:
        input_dict = json.loads(input_data)
    else:
        input_dict = input_data
    logger.debug("Received Input Info:%s"%(str(input_dict)))

    if is_unique_rtsp(input_dict["rtsp_url"]):
        # Try to read the dicitonary and populate the elements
        try:
            camera_obj = cctv_camera.CctvCamera(input_dict["camera_name"], input_dict["email_list"], input_dict["sms_list"],
                input_dict["call_list"], input_dict["rtsp_url"], input_dict["http_url"], input_dict["floor"], 
                input_dict["favourite"], input_dict["object_detect"], input_dict["intrusion_start_time"], 
                input_dict["intrusion_end_time"], input_dict["sound_alarm"], existing_id)
    
            p = StoppableThread(target=detect_object, args=(camera_obj, yolo_q), name=camera_obj.camera_name)

            # Add the camera object to ActiveCameras dictionary
            ActiveCameras[camera_obj.camera_id] = (camera_obj, p)
            
            # Add the camera info into camera database if it does not exists
            if existing_id is None:
                cdb.insert(camera_obj.camera_id, camera_obj.get_camera_info())

            p.start()
            return_dict["status"] = True
        
        except Exception as ex:
            print ex
            logger.error(ex.message)
    
    else:
        err_text = "RTSP URL:%s is not unique"%(input_dict["rtsp_url"])
        logger.error(err_text)
        return_dict["reason"] = err_text
    
    return return_dict

def delete_camera(camera_id, delete_from_db=True):
    '''Stop the camera if it is running and remove it from the ActiveCameras dictionary'''
    return_dict = {"status":False}
    logger.debug("Delete camera_id:%d"%(camera_id))

    if camera_id in ActiveCameras:
        camera_obj, p = ActiveCameras[camera_id]

        # Remove the camera info from ActiveCameras dictionary
        del ActiveCameras[camera_id]
        
        # Remove the camera info from camera database
        if delete_from_db:
            cdb.delete(camera_obj.camera_id)
            logger.info("Camera:%s has been deleted"%(camera_id))
            
        if p.is_alive():
            p.join()
        
        return_dict["status"] = True

    else:
        logger.warning("Camera:%d not present!"%(camera_id))

    return return_dict

def edit_camera(camera_id, json_data):
    '''Edit a camera by deleting the old camera object and creating a new one'''
    return_dict = {"status":False}

    try:
        input_dict = json.loads(json_data)
        logger.debug("Received Input Info:%s for camera_id:%d"%(str(input_dict), camera_id))

        if camera_id in ActiveCameras:
            camera_obj, p = ActiveCameras[camera_id]
            
            # Delete camera info only from ActiveCameras and not the database
            delete_camera(camera_id, delete_from_db=False)

            if is_unique_rtsp(input_dict["rtsp_url"]):

                camera_obj.edit_cctv_params(input_dict["camera_name"], input_dict["email_list"], input_dict["sms_list"],
                    input_dict["call_list"], input_dict["rtsp_url"], input_dict["http_url"], input_dict["floor"],
                    input_dict["favourite"], input_dict["object_detect"], input_dict["intrusion_start_time"],
                    input_dict["intrusion_end_time"], input_dict["sound_alarm"])

                p = StoppableThread(target=detect_object, args=(camera_obj, yolo_q), name=camera_obj.camera_name)

                # Edit the camera info in ActiveCameras dictionary
                ActiveCameras[camera_obj.camera_id] = (camera_obj, p)

                # Edit the camera info in camera database
                cdb.edit(camera_obj.camera_id, camera_obj.get_camera_info())

                p.start()
                return_dict["status"] = True

            else:
                err_text = "RTSP URL:%s is not unique"%(input_dict["rtsp_url"])
                logger.error(err_text)
                return_dict["reason"] = err_text

    except Exception as ex:
        logger.error(ex.message)
    
    return return_dict

def delete_all_cameras(delete_from_db=True):
    '''Delete all running cameras'''
    while (len(ActiveCameras) > 0):
        for key in ActiveCameras:
            delete_camera(key, delete_from_db=delete_from_db)
            break

def get_camera_info(camera_id):
    '''Return camera info for camera_id'''
    if camera_id in ActiveCameras:
        camera_obj, p = ActiveCameras[camera_id]
        return camera_obj.get_camera_info()
    
    return {}

def get_all_camera_info():
    '''Return all camera info'''
    return_dict = {}
    for key, value in ActiveCameras.iteritems():
        camera_obj, p = value
        return_dict[camera_obj.camera_id] = camera_obj.get_camera_info()

    return return_dict

def get_alert_info():
    '''Return the info for alerts and the camera which generated them. Once returned, empty the info'''
    return return_alert_info()

def detect_object(camera_obj, mod_q):
    '''Detect objects and generate alerts if threshold has crossed'''

    # Process feed only if detection is enabled
    if not is_any_detection_enabled(camera_obj.object_detect):
        logger.info("No Object detection enabled. Not processing feed...")
        return

    t = threading.currentThread()
    display_tid(t.name, get_tid())
    performance.add_thread()

    vcap = camera_obj.get_video_cap()
    
    frame_count = 0
    last_detection_frame = 0
    last_person_detection_frame = 0
    
    # Initialize first two frames with None
    t0 = None
    t1 = None
    ret = False

    # Error flags
    ERROR_FLAG = False

    main_start = time.time()

    # Keep running detection thread as long as stop event not occurred
    while (not t.stopped()):
        # Try to open the video stream
        if not vcap.isOpened() or ERROR_FLAG:
            ERROR_FLAG = False
            ret = False
            waitTime = 1
            while ret == False and not t.stopped():
                logger.error("Could not read video capture for %s. Retrying after %d second..."%(camera_obj.camera_name, waitTime))
                time.sleep(waitTime)
                vcap = camera_obj.get_video_cap()
                ret, t2 = vcap.read()

                if waitTime < 5:
                    waitTime = waitTime+1
            
        try:
            fps = int(vcap.get(cv2.CAP_PROP_FPS))

            # Since analog cameras aren't returning a normal fps value
            if fps > 30:
                fps = 30

            frame_rate = camera_obj.get_frame_rate()
            frame_per_window = int(fps/frame_rate)

            # Read the third image
            ret2, t2 = vcap.read()
            
            if not ret2:
                logger.error("Could not read the video frames for %s"%(camera_obj.camera_name))
                ERROR_FLAG = True
                time.sleep(0.5) # Avoid high CPU usage
                continue
    
            # Process frames as per the camera's sensitivity settings
            if frame_count%frame_per_window == 0:
                height, width, _ = t2.shape
                if height > MIN_HEIGHT_DIM:
                    factor = MIN_HEIGHT_DIM/float(height)
                    t2 = cv2.resize(t2, None, fx=factor, fy=factor) 
                logger.debug("Camera %s frame num to process:%d"%(camera_obj.camera_name, frame_count))
    
                # Main call to motion predict
                object_dict = camera_obj.object_detect.copy()
                del object_dict["intrusion"]

                # if 1 in object_dict.values() and ((t0!=None) and (t1!=None) and (t2!=None)):
                #     performance.fps_log('Calling Inception for %s'%(t.name))    
                    
                #     image, pred_dict = motion_predict.extract_feature(t0, t1, t2)
                #     if pred_dict is not None:
    
                #         logger.debug("Camera %s Prediction Dict:%s"%(camera_obj.camera_name, str(pred_dict)))
        
                #         for obj, detection_status in object_dict.iteritems():
                #             if detection_status == DETECTION_STATUS_ON and any(obj in key for key in pred_dict):
                #                 predict_obj = [key for key in pred_dict if obj in key][0]
                #                 prediction_val = pred_dict[predict_obj]
                #                 logger.debug("Detected object:%s with confidence=%f and detection threshold=%f"%(obj, 
                #                     prediction_val, DETECTION_THRESHOLD))
                                
                #                 if prediction_val > DETECTION_THRESHOLD:
                #                     if last_detection_frame == 0 or (frame_count - last_detection_frame)/fps > MIN_DETECT_INTERVAL:
                #                         notify_detection(image, camera_obj, obj, prediction_val)
                #                         last_detection_frame = frame_count
                                                   
                # Check if intrusion is enabled and time is satisfied
                if camera_obj.is_intrusion_enabled():
                	#mod_q.put((camera_obj.camera_id, camera_obj.camera_name, camera_obj.email_list, camera_obj.sms_list, camera_obj.call_list, frame_count, fps, t2), block=False)

                    im = darknet.array_to_image(t2)
                    darknet.rgbgr_image(im)
                    mod_q.put((camera_obj.camera_id, camera_obj.camera_name, camera_obj.email_list, camera_obj.sms_list, camera_obj.call_list, frame_count, fps, t2, im), block=False)

                # Pass on the old values
                t0 = t1
                t1 = t2
            
            frame_count += 1
            
            
        except Queue.Full:
            logger.error("The detection Queueu is full! Max Size:%d reached"%(MAX_Q_SZ))
        except Exception as ex:
            ERROR_FLAG = True
            time.sleep(0.5) # Avoid high CPU usage
            logger.error(ex.message)
    
    print bgcolors.FAIL + 'Clean up from %s'%t.name + bgcolors.ENDC

    vcap.release()
    cv2.destroyAllWindows()


def get_frame(camera_id):
    '''For the given camera id, return the frame in jpeg format'''
    if camera_id in ActiveCameras:
        camera_obj, p = ActiveCameras[camera_id]
        try:
            success, image = camera_obj.vcap.read()
            ret, jpeg = cv2.imencode('.jpg', image)
            return jpeg.tobytes()

        except Exception as ex:
            logger.error("For camera %s. "%(camera_obj.camera_name) + str(ex.message))
            return None
    else:
        return None

def is_unique_rtsp(rtsp_url):
    '''Check if the given rtsp url is not currently being used by any other camera'''
    ret = True
    for key, (camera_obj,p) in ActiveCameras.iteritems():
        if camera_obj.rtsp_url == rtsp_url:
            ret = False
            break

    return ret

def is_any_detection_enabled(obj_dict):
    '''Check if any detection is enabled'''
    for key,value in obj_dict.iteritems():
        if value == 1:
            return True
    return False
