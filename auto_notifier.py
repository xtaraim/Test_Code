'''
Filename: auto_notifier.py
Description: This module handles the response, such as call, SMS and email, sent to the user when an intrusion is detected. 
'''

import os
import smtplib
import string
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from twilio.rest import Client
from config import get_config
import logging
from threading import current_thread, active_count
from utils import *
from utils import bgcolors as bg
import Queue
import time
import json
import requests
import datetime
import performance
import auto_testcases
import run_testcases
# Your Account SID from twilio.com/console
account_sid = get_config('auto_notifier', 'account_sid')

# Your Auth Token from twilio.com/console
auth_token  = get_config('auto_notifier', 'auth_token')
default_twilio_url = get_config('auto_notifier', 'default_twilio_url')
default_twilio_from = get_config('auto_notifier', 'default_twilio_from')

EMAIL_USERNAME = get_config('auto_notifier', 'EMAIL_USERNAME')
EMAIL_PASSWORD = get_config('auto_notifier', 'EMAIL_PASSWORD')
TEXTLOCAL_USERNAME = get_config('auto_notifier', 'TEXTLOCAL_USERNAME')
TEXTLOCAL_PASSWORD = get_config('auto_notifier', 'TEXTLOCAL_PASSWORD')
CALL_GAP_TIME = int(get_config('auto_notifier', 'CALL_GAP_TIME'))
MAX_CALL_SAME_NUM_BUFFER = int(get_config('auto_notifier', 'MAX_CALL_SAME_NUM_BUFFER'))
MIN_EMAIL_Q_PERCENT = int(get_config('auto_notifier', 'MIN_EMAIL_Q_PERCENT'))
MIN_SMS_Q_PERCENT = int(get_config('auto_notifier', 'MIN_SMS_Q_PERCENT'))
MIN_CALL_Q_PERCENT = int(get_config('auto_notifier', 'MIN_CALL_Q_PERCENT'))
MIN_Q_TIMEOUT = int(get_config('auto_notifier', 'MIN_Q_TIMEOUT'))

if get_config('auto_notifier', 'USE_IMI') == "True":
    USE_IMI = True
else:
    USE_IMI = False

# IMI Mobile API Key
API_KEY = get_config('auto_notifier', 'API_KEY')

# Monitor thread object
mon_t = None
log_run = 0

def monitor_thread():
    '''This thread spawns and monitors the notification threads and respawns them if they crash'''
    t = current_thread()
    display_tid(t.name, get_tid())
    performance.add_thread()
    logging.info("Starting monitoring thread: %s"%(t.name))

    if USE_IMI:
       call_method = call_imi
    else:
       call_method = call_twilio
    sms_method = sms_textlocal

    # Add the respective queues for performance
    performance.add_call_q(call_q)
    performance.add_sms_q(sms_q)
    performance.add_email_q(email_q)

    # Create the three notification threads
    email_thread = StoppableThread(target=sendEmail, name="Email-Thread")
    call_thread = StoppableThread(target=call_method, name="Call-Thread")
    sms_thread = StoppableThread(target=sms_method, name="SMS-Thread")

    # Add the threads to the monitoring dicitonary
    monitor_dict = {
        "Email-Thread": email_thread,
        "Call-Thread": call_thread,
        "SMS-Thread": sms_thread
        }

    # Start the threads
    logging.info("Starting notifier threads...")
    for thread_name, _thread in monitor_dict.iteritems():
        _thread.start()

    # Monitor the thread for activity
    while (not t.stopped()):
        time.sleep(1)
        for thread_name, _thread in monitor_dict.iteritems():
            if not _thread.is_alive():
                try:
                    if thread_name == "Email-Thread":
                        # Close existing thread
                        _thread.join()

                        # Restart new thread
                        logging.warning("Re-starting Email-Thread")
                        print bg.FAIL + '\nRe-starting Email-Thread' + bg.ENDC

                        email_thread = StoppableThread(target=sendEmail, name='Email-Thread')
                        monitor_dict["Email-Thread"] = email_thread
                        email_thread.start()
                    
                    elif thread_name == "Call-Thread":
                        # Close existing thread
                        _thread.join()

                        # Restart new thread
                        logging.warning("Re-starting Call-Thread")
                        print bg.FAIL + '\nRe-starting Call-Thread' + bg.ENDC

                        call_thread = StoppableThread(target=call_method, name='Call-Thread')
                        monitor_dict["Call-Thread"] = call_thread
                        call_thread.start()
                    
                    elif thread_name == "SMS-Thread":
                        # Close existing thread
                        _thread.join()

                        # Restart new thread
                        logging.warning("Re-starting SMS-Thread")
                        print bg.FAIL + '\nRe-starting SMS-Thread' + bg.ENDC

                        sms_thread = StoppableThread(target=sms_method, name='SMS-Thread')
                        monitor_dict["SMS-Thread"] = sms_thread
                        sms_thread.start()

                except Exception as ex:
                    print ex
                    logging.error(ex.message)

    print bg.FAIL + '\nClean up from monitor thread' + bg.ENDC
    for thread_name, _thread in monitor_dict.iteritems():
        _thread.join()

def start_monitor_thread():
    global mon_t
    mon_t = StoppableThread(target=monitor_thread, name='Monitor-Thread')
    mon_t.start()

def stop_monitor_thread():
    global mon_t
    print bg.FAIL + '\nExiting monitor thread' + bg.ENDC
    
    try:
        if mon_t.is_alive():
            mon_t.join()
            mon_t = None
    except Exception as e:
        print e

    print bg.OKGREEN + 'Done stopping monitor thread' + bg.ENDC

def sendEmail():
    '''
    This sents a mail a message to the mail ids in "toAddressList" with the details of intrusion 
    and an image capturing the intruder.
    '''
    t = current_thread()
    display_tid(t.name, get_tid())
    performance.add_thread()
    logging.info("Starting email thread: %s"%(t.name))
    error_flag = True
    start_time = time.time()
    print run_testcases.flag
    #toAddressList, objectType, detectionTime, camera_name, detectionAcuracy, imageName = email_q.get(block=True, timeout=MIN_Q_TIMEOUT)
    #auto_testcases.emaillist_automation(toAddressList,len(toAddressList),MAX_EMAIL_Q_SZ,email_q.qsize())
    while (not t.stopped()):
        try:
            # If the MAX_EMAIL_Q_SZ has been reached, we have plenty of buffered items which will take too
            # long to process. In this scenario, reduce the Queue to include only the latest 'MIN_EMAIL_Q_PERCENT' 
            # items to be processed
            if email_q.qsize() == MAX_EMAIL_Q_SZ:
                reduce_items = int(MAX_EMAIL_Q_SZ - (MIN_EMAIL_Q_PERCENT*MAX_EMAIL_Q_SZ/float(100)))
                logger.info("Max email q size reached:%d removing oldest %d items"%(MAX_EMAIL_Q_SZ, reduce_items))
                for _ in range(reduce_items):
                    _, _, _, _, _, _ = email_q.get()
                

            toAddressList, objectType, detectionTime, camera_name, detectionAcuracy, imageName = email_q.get(block=True, timeout=MIN_Q_TIMEOUT)
            if(time.time()>start_time+40):
                print "Send mail testing"
                if(6 in run_testcases.flag):
                    auto_testcases.emaillist_automation(toAddressList,len(toAddressList),MAX_EMAIL_Q_SZ,email_q.qsize()+1)
                start_time = time.time()

            def timeout_email(toAddressList, objectType, detectionTime, camera_name, detectionAcuracy, imageName):
                Subj = "%s Detection Alarm!!!"%(objectType.title())
                Text = "%s detected at %s for camera %s  with %d%% accuracy. Please check attached image for reference."%(objectType.title(), detectionTime, camera_name, detectionAcuracy)

                msg = MIMEMultipart()
                msg['Subject'] = Subj
                msg['From'] = EMAIL_USERNAME
                msg['To'] = ", ".join(toAddressList)
                
                msg.attach(MIMEText(Text))
                
                with open(imageName, "rb") as fil:
                    part = MIMEApplication(fil.read(), Name=basename(imageName))
                part['Content-Disposition'] = 'attachment; filename="%s"'%(basename(imageName))
                msg.attach(part)
                
                error_flag = True
                while error_flag:
                    try:
                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.ehlo()
                        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                    except Exception as ex:
                        logger.error(ex)
                        server.quit()
                    else:
                        error_flag = False

                server.sendmail(EMAIL_USERNAME, toAddressList, msg.as_string())
                logging.info("Sending email to: %s with content: %s"%(toAddressList, Text))

            timeout(timeout_email, (toAddressList, objectType, detectionTime, camera_name, detectionAcuracy, imageName))

        except Queue.Empty as ex:
            pass

        except Exception as ex:
            print ex
            logging.error(ex)
            error_flag = True
            time.sleep(1)

    print "Stopping Email thread: %s"%(t.name)
    logging.info("Stopping email thread: %s"%(t.name))


def sms_textlocal(): 
    '''
    This sents a SMS to the numbers in "toAddressList" using text_local
    '''
    t = current_thread()
    display_tid(t.name, get_tid())
    performance.add_thread()
    logging.info("Starting SMS thread: %s"%(t.name))
    error_flag = True
    #toAddressList, objectType, detectionTime, camera_name, detectionAcuracy = sms_q.get(block=True, timeout=MIN_Q_TIMEOUT)
    #auto_testcases.smslist_automation(toAddressList,len(toAddressList),MAX_SMS_Q_SZ,sms_q.qsize())
    start_time = time.time()
    while (not t.stopped()):
        try:

            # If the MAX_SMS_Q_SZ has been reached, we have plenty of buffered items which will take too
            # long to process. In this scenario, reduce the Queue to include only the latest 'MIN_SMS_Q_PERCENT' 
            # items to be processed
            if sms_q.qsize() == MAX_SMS_Q_SZ:
                reduce_items = int(MAX_SMS_Q_SZ - (MIN_SMS_Q_PERCENT*MAX_SMS_Q_SZ/float(100)))
                logger.info("Max sms q size reached:%d removing oldest %d items"%(MAX_SMS_Q_SZ, reduce_items))
                for _ in range(reduce_items):
                    _, _, _, _, _ = sms_q.get()
                
            toAddressList, objectType, detectionTime, camera_name, detectionAcuracy = sms_q.get(block=True, timeout=MIN_Q_TIMEOUT)
            if(time.time()>start_time+40):
                if(5 in run_testcases.flag):
                    auto_testcases.smslist_automation(toAddressList,len(toAddressList),MAX_SMS_Q_SZ,sms_q.qsize()+1)
                start_time = time.time()
            def timeout_sms(toAddressList, objectType, detectionTime, camera_name, detectionAcuracy):

                Subj = "%s Detection Alarm!!!"%(objectType.title())
                Text = "%s detected at %s for camera %s with %d%% accuracy."%(objectType.title(), detectionTime, camera_name, detectionAcuracy)
                
                toAddressList = [str(str(toAddress) + "@sms.textlocal.in") for toAddress in toAddressList]
                msg = MIMEMultipart()
                msg['Subject'] = Subj
                msg['From'] = TEXTLOCAL_USERNAME
                msg['To'] = ", ".join(toAddressList)
                
                msg.attach(MIMEText(Text))
            
                error_flag = True
                while error_flag:
                    try:
                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.ehlo()
                        server.login(TEXTLOCAL_USERNAME, TEXTLOCAL_PASSWORD)
                    except Exception as ex:
                        logger.error(ex)
                        server.quit()
                    else:
                        error_flag = False

                server.sendmail(TEXTLOCAL_USERNAME, toAddressList, msg.as_string())
                logging.info("Sending SMS to: %s with content: %s"%(toAddressList, Text))

            timeout(timeout_sms, (toAddressList, objectType, detectionTime, camera_name, detectionAcuracy))

        except Queue.Empty as ex:
            pass

        except Exception as ex:
            print ex
            logging.error(ex)
            error_flag = True
            time.sleep(1)

    logging.info("Stopping SMS thread: %s"%(t.name))

def call_twilio():
    '''
    This function calls all the numbers in the call_list using twilio
    '''
    t = current_thread()
    display_tid(t.name, get_tid())
    performance.add_thread()
    logging.info("Starting Call thread: %s"%(t.name))

    caller_dict = {}
    call_count_dict = {}
    
    while (not t.stopped()):
        try:
            new_call_list = []
            # If the MAX_CALL_Q_SZ has been reached, we have plenty of buffered items which will take too
            # long to process. In this scenario, reduce the Queue to include only the latest 'MIN_CALL_Q_PERCENT' 
            # items to be processed
            if call_q.qsize() == MAX_CALL_Q_SZ:
                reduce_items = int(MAX_CALL_Q_SZ - (MIN_CALL_Q_PERCENT*MAX_CALL_Q_SZ/float(100)))
                logger.info("Max call q size reached:%d removing oldest %d items"%(MAX_CALL_Q_SZ, reduce_items))
                for _ in range(reduce_items):
                     _, _ = call_q.get()
                
            call_list, objectType = call_q.get(block=True, timeout=MIN_Q_TIMEOUT)

            def call_timeout(call_list, objectType, caller_dict, call_count_dict):
                client = Client(account_sid, auth_token)
        
                if objectType == "intrusion":
                    objectType = "int"
        
                xml_file = default_twilio_url + objectType + ".xml"
                for callee in call_list:
                    if callee not in caller_dict or (callee in caller_dict and time.time() - caller_dict[callee] > CALL_GAP_TIME):
                        called_party = str("+91" + callee)
                        logging.debug("called_party:%s default_twilio_from:%s xml_file:%s"%(called_party, default_twilio_from, xml_file))
                        call = client.calls.create(to=called_party, from_=default_twilio_from, url=xml_file)
                        caller_dict[callee] = time.time()
                        
                        # A buffered call has been processsed, so reduce the buffered call count
                        if callee in call_count_dict:
                            call_count_dict[callee] = call_count_dict[callee] - 1
                    else:
                        # Only store a maximum of 10 elements of a particular caller.
                        # Do not keep storing a caller indefinitely
                        if callee in call_count_dict and call_count_dict[callee] < MAX_CALL_SAME_NUM_BUFFER:
                           call_count_dict[callee] = call_count_dict[callee] + 1
                        elif callee not in call_count_dict:
                           call_count_dict[callee] = 1
    
                        if call_count_dict[callee] <= MAX_CALL_SAME_NUM_BUFFER:
                           new_call_list.append(callee)
                
                if new_call_list:
                    call_q.put((new_call_list, objectType))

            timeout(call_timeout, (call_list, objectType, caller_dict, call_count_dict))

        except Queue.Empty as ex:
            pass

        except Exception as ex:
            print ex
            logging.error(ex)
            time.sleep(1)

    logging.info("Stopping Call thread: %s"%(t.name))

def sms_imi():
    '''
    This sents a SMS to the numbers in "toAddressList" using IMI services
    '''
    t = current_thread()
    display_tid(t.name, get_tid())
    performance.add_thread()
    logging.info("Starting SMS thread: %s"%(t.name))

    while (not t.stopped()):
        try:
            # If the MAX_SMS_Q_SZ has been reached, we have plenty of buffered items which will take too
            # long to process. In this scenario, reduce the Queue to include only the latest 'MIN_SMS_Q_PERCENT' 
            # items to be processed
            if sms_q.qsize() == MAX_SMS_Q_SZ:
                reduce_items = int(MAX_SMS_Q_SZ - (MIN_SMS_Q_PERCENT*MAX_SMS_Q_SZ/float(100)))
                logger.info("Max sms q size reached:%d removing oldest %d items"%(MAX_SMS_Q_SZ, reduce_items))
                for _ in range(reduce_items):
                    _, _, _, _, _ = sms_q.get()
                
            toAddressList, objectType, detectionTime, camera_name, detectionAcuracy = sms_q.get(block=True, timeout=MIN_Q_TIMEOUT)

            Subj = "%s Detection Alarm!!!\n\n"%(objectType.title())
            Text = "%s detected at %s for camera '%s' with %d%% accuracy."%(objectType.title(), 
                detectionTime, camera_name, detectionAcuracy)
            Text += "\n\nFrom Deep Sight AI Labs"
            Message = Subj + Text

            apiurl = 'http://api-openhouse.imimobile.com/smsmessaging/1/outbound/tel%3A%2Bopnhse/requests'


            for toAddress in toAddressList:
                called_party = '91' + toAddress
                print '\nSending notification SMS to %s with content:\n------------\n%s\n------------'%(called_party, Message)

                #JSON object to be sent in the POST body.
                rawdata =   {
                                'outboundSMSMessageRequest':
                                {
                                    'address':'tel:' + called_party,
                                    'senderAddress':'tel:OPNHSE',
                                    'senderName':'DSLABS',
                                    'outboundSMSTextMessage':
                                    {
                                        'message':Message
                                    }
                                }
                            }

                headers =   {
                                'key':API_KEY,
                                'Content-type':'application/json',
                                'Accept':'application/json'
                            }
                
                r = requests.post(apiurl, data=json.dumps(rawdata), headers=headers)
                uuid = None
                try: 
                    uuid = r.text[r.text.index('urn:uuid:'):][:r.text[r.text.index('urn:uuid:'):].index('\\')]
                    print 'IMI SMS JSON response:', uuid
                except: 
                    print 'IMI SMS JSON response:', r.text       
                
                logging.debug("Sending SMS to: %s with content: %s"%(toAddress, Message))
                logging.debug("JSON Response UUID: %s"%(uuid))

        except Queue.Empty as ex:
            pass

        except Exception as ex:
            print ex
            logging.error(ex.message)
            time.sleep(0.5)

    print "Stopping SMS thread: %s"%(t.name)
    logging.info("Stopping SMS thread: %s"%(t.name))

def call_imi():
    '''
    This function calls all the numbers in the call_list using IMI services
    '''
    t = current_thread()
    display_tid(t.name, get_tid())
    performance.add_thread()
    logging.info("Starting Call thread: %s"%(t.name))
    caller_dict = {}
    call_count_dict = {}
    #call_list, objectType = call_q.get(block=True, timeout=MIN_Q_TIMEOUT)
    #auto_testcases.calllist_automation(False,1,call_list,len(call_list),MAX_CALL_Q_SZ,call_q.qsize()) 
    start_time = time.time()
    call_time_gap_flag = True
    call_time_gap = 1
    
    while (not t.stopped()):
        try:
            # If the MAX_CALL_Q_SZ has been reached, we have plenty of buffered items which will take too
            # long to process. In this scenario, reduce the Queue to include only the latest 'MIN_CALL_Q_PERCENT' 
            # items to be processed
            if call_q.qsize() == MAX_CALL_Q_SZ:
                reduce_items = int(MAX_CALL_Q_SZ - (MIN_CALL_Q_PERCENT*MAX_CALL_Q_SZ/float(100)))
                logger.info("Max call q size reached:%d removing oldest %d items"%(MAX_CALL_Q_SZ, reduce_items))
                for _ in range(reduce_items):
                     _, _ = call_q.get()
                
            call_list, objectType = call_q.get(block=True, timeout=MIN_Q_TIMEOUT)
            if(time.time()>start_time+40):
                if(4 in run_testcases.flag):
                    auto_testcases.calllist_automation(call_time_gap_flag,call_time_gap,call_list,len(call_list),MAX_CALL_Q_SZ,call_q.qsize()+1)  
                start_time = time.time()
 
            def timeout_call(call_list, objectType, caller_dict, call_count_dict):
                apiurl= "http://api-openhouse.imimobile.com/1/obd/thirdpartycall/callSessions"
                mode='Media'
                new_call_list = []
                for callee in call_list:
                    if callee not in caller_dict or (callee in caller_dict and time.time() - caller_dict[callee] > CALL_GAP_TIME):
                        called_party = '91' + callee
                        logging.debug("Calling: %s for object: %s"%(called_party, objectType))
                        print bgcolors.OKGREEN + '\nCalling %s, alerting for %s'%(called_party, objectType) + bgcolors.ENDC
        
                        #rawdata ="address=%(Mobile)s&medianame=%(medianame)s&mode=%(mode)s" % dict(Mobile=called_party,
                        rawdata ="address=%(Mobile)s&mode=%(mode)s&patternId=0&medianame=%(medianame)s" % dict(Mobile=called_party,
                            mode=mode,medianame=objectType)
                        headers = {'key':API_KEY, 'Content-type':'application/x-www-form-urlencoded'}
                        r = requests.post(apiurl, data=json.dumps(rawdata).replace("\"",""), headers=headers)
                        #print "Ritwik:", apiurl, json.dumps(rawdata).replace("\"",""), headers
                        print 'IMI call JSON response: %s\n'%(r.text)
        
                        logging.debug("JSON Response UUID: %s"%(r.text))
                        caller_dict[callee] = time.time()

                        # A buffered call has been processsed, so reduce the buffered call count
                        if callee in call_count_dict:
                            call_count_dict[callee] = call_count_dict[callee] - 1

                    else:
                        # Only store a maximum of 10 elements of a particular caller.
                        # Do not keep storing a caller indefinitely
                        if callee in call_count_dict and call_count_dict[callee] < MAX_CALL_SAME_NUM_BUFFER:
                           call_count_dict[callee] = call_count_dict[callee] + 1
                        elif callee not in call_count_dict:
                           call_count_dict[callee] = 1

                        if call_count_dict[callee] <= MAX_CALL_SAME_NUM_BUFFER:
                           new_call_list.append(callee)
                
                if new_call_list:
                    call_q.put((new_call_list, objectType))

            timeout(timeout_call, (call_list, objectType, caller_dict, call_count_dict))

        except Queue.Empty as ex:
            pass

        except Exception as ex:
            print ex
            logging.error(ex)
            time.sleep(1)

    print "Stopping Call thread: %s"%(t.name)
    logging.info("Stopping Call thread: %s"%(t.name))

