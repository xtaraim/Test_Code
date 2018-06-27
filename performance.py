import os
import csv
import time
import psutil
import datetime
import subprocess
import auto_testcases
import run_testcases
# For developer mode only
if __name__ == '__main__':
    # Import config
    import config

    # Set base directory
    config.set_base_dir(os.path.dirname(os.path.realpath(__file__)))

    # Set resource directory
    config.set_resource_dir()

    # Initialize configurations
    config.config_init()

from utils import *

# TODO: Replace with config
PERF_FOLDER = 'perf_logs'
THREAD_LIST_FILE = 'perf_logs/threads.list'
CPU_LOG_FILE = 'perf_logs/cpu.log'
GPU_LOG_FILE = 'perf_logs/gpu.log'
FPS_LOG_FILE = 'perf_logs/fps.log'
FPS_LOG_FIRST_TIME = True

# Main PID and psutils object
MAIN_PID = os.getpid()
MAIN_UTIL = psutil.Process(MAIN_PID)

# Threads info list
# Format --> [TID, Name, Usage]
THREADS = []

# Performance logger threads
CPU_THREAD = None
GPU_THREAD = None
ADD_LOCK = threading.Lock()

DETECTION_Q = None
EMAIL_Q = None
SMS_Q = None
CALL_Q = None



def initialize_performance(interval=1):
    global CPU_THREAD, GPU_THREAD

    # Create perf log folder
    if not os.path.exists(PERF_FOLDER):
        print 'Creating performance log folder at %s%s%s...'%(bgcolors.BOLD + bgcolors.OKBLUE, PERF_FOLDER, bgcolors.ENDC)
        os.makedirs(PERF_FOLDER)
        print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

    # Create threads.list file
    if not os.path.exists(THREAD_LIST_FILE):
        print 'Creating %s%s%s...'%(bgcolors.BOLD + bgcolors.OKBLUE, THREAD_LIST_FILE, bgcolors.ENDC)
        os.mknod(THREAD_LIST_FILE)
        print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC 

    # Create cpu.log file
    if not os.path.exists(CPU_LOG_FILE):
        print 'Creating %s%s%s...'%(bgcolors.BOLD + bgcolors.OKBLUE, CPU_LOG_FILE, bgcolors.ENDC)
        os.mknod(CPU_LOG_FILE)
        print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

    # Create gpu.log file
    if not os.path.exists(GPU_LOG_FILE):
        print 'Creating %s%s%s...'%(bgcolors.BOLD + bgcolors.OKBLUE, GPU_LOG_FILE, bgcolors.ENDC)
        os.mknod(GPU_LOG_FILE)
        print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

    # Create fps.log file
    if not os.path.exists(FPS_LOG_FILE):
        print 'Creating %s%s%s...'%(bgcolors.BOLD + bgcolors.OKBLUE, FPS_LOG_FILE, bgcolors.ENDC)
        os.mknod(FPS_LOG_FILE)
        print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

    # Start CPU logger thread
    print bgcolors.OKBLUE + 'Starting CPU logger thread' + bgcolors.ENDC
    CPU_THREAD = StoppableThread(name='CPU-Logger', target=cpu_log, args=(interval,))
    CPU_THREAD.start()
    print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

    # Start GPU logger thread
    print bgcolors.OKBLUE + 'Starting GPU logger thread' + bgcolors.ENDC
    GPU_THREAD = StoppableThread(name='GPU-Logger', target=gpu_log, args=(interval,))
    GPU_THREAD.start()
    print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC

    # Add main thread to THREADS list
    add_thread(mode='w+')

def add_detect_q(q):
    global DETECTION_Q
    DETECTION_Q = q

def add_call_q(q):
    global CALL_Q
    CALL_Q = q

def add_sms_q(q):
    global SMS_Q
    SMS_Q = q

def add_email_q(q):
    global EMAIL_Q
    EMAIL_Q = q

def deinitialize_performance():
    global CPU_THREAD, GPU_THREAD

    print bgcolors.OKBLUE + '\nStopping performace logger threads' + bgcolors.ENDC

    try:
        if CPU_THREAD.is_alive():
            CPU_THREAD.join()
            CPU_THREAD = None
            print bgcolors.OKGREEN + 'CPU Done\n' + bgcolors.ENDC

        if GPU_THREAD.is_alive():
            GPU_THREAD.join()
            GPU_THREAD = None
            print bgcolors.OKGREEN + 'GPU Done\n' + bgcolors.ENDC

    except Exception as e: 
        print e

def read_csv(filename):
    '''Read from CSV file'''
    csv_file = open(filename, 'r')
    data = list(csv.reader(csv_file))
    csv_file.close()
    return data

def write_csv(filename, data, mode='a+'):
    '''Write to CSV file'''
    csv_file = open(filename, mode)
    writer = csv.writer(csv_file)
    writer.writerows([data])
    csv_file.close()

def write_file(filename, data, mode='a+'):
    with open(filename, mode) as f:
        f.write(data)

def add_thread(mode='a+'):
    '''This function should only be called from within another thread'''

    ADD_LOCK.acquire()

    # Get current thread details
    th = threading.currentThread()
    tid = get_tid()
    print 'Adding Thread: %s with TID: %d'%(th.name, tid)

    # Add to THREADS list
    THREADS.append([tid, th.name, None])

    # Add to threads.list
    write_csv(THREAD_LIST_FILE, [tid, th.name], mode=mode)

    ADD_LOCK.release()

def cpu_log(interval):
    # Display performace logger TID
    print 'CPU Logger TID:', get_tid()
    # Add headers
    data = ['Timestamp', 'TID', 'Thread Name', 'CPU Usage', 'Memory Usage (GB)', 'Total Memory (GB)', 'Memory Usage (%)']
    write_csv(CPU_LOG_FILE, data, mode='w+')
    start_time = time.time()
    t = threading.currentThread()
    prev_total_percent = 0
    total_percent = 0
    while (not t.stopped()):
        try:
            prev_total_percent = total_percent
            total_percent = MAIN_UTIL.cpu_percent()
            if(time.time()>start_time+40):
                if(3 in run_testcases.flag):
                    auto_testcases.FPS_automation()
                if(7 in run_testcases.flag):
                    auto_testcases.get_CPUusage_details(prev_total_percent,total_percent)
                start_time = time.time()
            total_time = sum(MAIN_UTIL.cpu_times())
            thread_usage = []
            
            for th in MAIN_UTIL.threads():
                for _th in THREADS:
                    if _th[0] == th.id:
                        data = [None]*7

                        _th[2] = total_percent * ((th.system_time + th.user_time)/total_time)
    
                        # Timestamp
                        data[0] = datetime.datetime.now().isoformat(' ')

                        # Thread ID
                        data[1] = _th[0]

                        # Thread Name
                        data[2] = _th[1]

                        # Thread CPU Usage
                        if _th[0] == MAIN_PID: data[3] = total_percent
                        else: data[3] = _th[2]

                        # Memory RSS (GB)
                        data[4] = MAIN_UTIL.memory_info().rss / (1024.0 ** 3)

                        # Memory Total (GB)
                        data[5] = psutil.virtual_memory().total / (1024.0 ** 3)

                        # Memory Percentage
                        data[6] = MAIN_UTIL.memory_percent()

                        # Write CSV file
                        write_csv(CPU_LOG_FILE, data)  

            if DETECTION_Q != None:
                q_str = "Detection Queue Size: %d\n"%DETECTION_Q.qsize()
                write_file(CPU_LOG_FILE, q_str)  

            if CALL_Q != None:
                q_str = "Call Queue Size: %d\n"%CALL_Q.qsize()
                write_file(CPU_LOG_FILE, q_str)  

            if SMS_Q != None:
                q_str = "SMS Queue Size: %d\n"%SMS_Q.qsize()
                write_file(CPU_LOG_FILE, q_str)  

            if EMAIL_Q != None:
                q_str = "Email Queue Size: %d\n"%EMAIL_Q.qsize()
                write_file(CPU_LOG_FILE, q_str)  


            time.sleep(interval)
        except Exception as e:
            print e


    print bgcolors.FAIL + 'Clean up from %s'%t.name + bgcolors.ENDC

def gpu_log(interval):
    # Display performace logger TID
    print 'GPU Logger TID:', get_tid()

    # GPU Commands
    gpu_usage_com = ['nvidia-smi', '--query-gpu=name,driver_version,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.free,memory.used', '--format=csv']
    gpu_process_usage_com = ['nvidia-smi', '--query-compute-apps=pid,used_memory', '--format=csv']

    # GPU Headers
    gpu_headers = ['Timestamp', 'GPU Name', 'GPU Driver Version', 'GPU Temperature', 'GPU Utilization', 
                   'GPU Memory Utilization', 'GPU Total Memory', 'GPU Free Memory', 
                   'GPU Used Memory', 'GPU PID', 'GPU Process Memory']

    write_csv(GPU_LOG_FILE, gpu_headers, mode='w+')    

    t = threading.currentThread()
    while (not t.stopped()):
        try:
            gpu_data = [datetime.datetime.now().isoformat(' ')]

            proc = subprocess.Popen(gpu_usage_com, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = proc.communicate()
            if proc.returncode == 0:        
                gpu_data += output[0].split('\n')[1].split(', ')

            proc = subprocess.Popen(gpu_process_usage_com, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = proc.communicate()
            if proc.returncode == 0:
                data = output[0].split('\n')[1].split(', ')
                try: 
                    pid = int(data[0])
                    if pid == MAIN_PID: gpu_data += data
                except: pass

            # Write CSV file
            write_csv(GPU_LOG_FILE, gpu_data)    
            time.sleep(interval)

        except Exception as e:
            print e

    print bgcolors.FAIL + 'Clean up from %s'%t.name + bgcolors.ENDC

def fps_log(msg1='', msg2='', msg3='', t=None):
    global FPS_LOG_FIRST_TIME

    try: 
        msg1 = str(msg1)
        msg2 = str(msg2)
        msg3 = str(msg3)
    except: pass

    if t is None:
        t = datetime.datetime.now().isoformat(' ')
    
    if FPS_LOG_FIRST_TIME:
        FPS_LOG_FIRST_TIME = False
        mode = 'w+'
    else:
        mode = 'a+'

    with open(FPS_LOG_FILE, mode) as f: 
        f.write('%s %s %s %s\n'%(t, msg1, msg2, msg3)) 

def func(ts):
    add_thread()
    th = threading.currentThread()

    while (not th.stopped()):
        if ts: time.sleep(ts)

    print bgcolors.FAIL + 'Clean up from %s'%th.name + bgcolors.ENDC

if __name__ == '__main__':
    initialize_performance()

    thread1 = StoppableThread(name='CAM-01', target=func, args=(1,))
    thread1.start()

    thread2 = StoppableThread(name='CAM-02', target=func, args=(None,))
    thread2.start()

    time.sleep(60)

    thread1.join()
    thread2.join()

    CPU_THREAD.join()
    GPU_THREAD.join()
