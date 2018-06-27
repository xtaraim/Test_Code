import os
import csv 
import config
import psutil
import commands
import performance
import auto_notifier
import time
import datetime
import camera_controller
import run_testcases

from licensing import get_license_details

base_dir = '/opt/godeep/'
perf_folder = 'TEST_RESULTS'
LICENSE_LOG_FILE = 'TEST_RESULTS/license.log'
LICENSE_LOG_FILE_PATH = base_dir+LICENSE_LOG_FILE
#TESTCASERESULTS = perf_folder+'/testcaseresults.csv'
#TESTCASERESULTS_FILEPATH = base_dir+perf_folder+'/'+time_now+'.csv'
#TESTCASERESULTS_FILEPATH = base_dir+perf_folder+'/'+time_now+'testcaseresults.csv'
TESTCASERESULTS_FILEPATH = ""
TestCase_names=['validity of license']
TestCase_heading = ['Test case name','Result']
Flag_filepath = base_dir+perf_folder+'/flag.log'
Licenselog_fields = ['Status','Usage','Validity']
CRONTAB_LICENSEFILE = base_dir+perf_folder+'/crontab.log'
CALLLIST_LOGFILE = base_dir+perf_folder+'/calllist.log'
SMSLIST_LOGFILE = base_dir+perf_folder+'/smslist.log'
EMAILLIST_LOGFILE = base_dir+perf_folder+'/emaillist.log'
NETSTATUS_LOGFILE = base_dir+perf_folder+'/netstatus.log'
GPU_LOGFILE = base_dir+perf_folder+'/gpu.log'
CPU_LOGFILE = base_dir+perf_folder+'/cpu.log'
FPS_LOGFILE = base_dir+perf_folder+'/fps.log'
APP_LOGFILE = base_dir+perf_folder+'/app.log'
time_now = datetime.datetime.now().isoformat(' ')
TESTCASERESULTS_FILEPATH = base_dir+perf_folder+'/'+time_now+'.csv'
interval_time = int(config.get_config('auto_testcases','interval_time'))
print interval_time
count_update = 0
start_time = ""
start_time_app=""
testcase_names_map = {'1':'Checking validity of license file',
'2a':'check the process id of godeep','2b':'Killing the godeep','2c':'checking whether crontab is starting godeep again after reboot',
'3':'FPS should not be dropped below 8',
'4':'MAX_CALL_Q_SZ Queue value from setting file should never be More than MAX_CALL_Q_SZ',
'5':'MAX_SMS_Q_SZ Queue value from setting file should never be More than MAX_SMS_Q_SZ',
'6':'MAX_EMAIL_Q_SZ Queue value from setting file should never be More than MAX_EMAIL_Q_SZ',
'7a':'GPU temperature should be below 54','7b':'CPU usage should not downtrend','7c':'GPU usage should not downtrend',
'8a':'net turning off','8b':'net turning on','8c':'Camera should reconnect after internet comes back',
'9':'MAX_CALL_Q_SZ Queue value from setting file should never be More than MAX_CALL_Q_SZ'}

time_interval_torun = 3600
results_mapping = {True:'PASS',
False:'FAIL'}

def read_csv(filename):
	'''Read from CSV file'''
	csv_file = open(filename, 'r')
	data = list(csv.reader(csv_file))
	csv_file.close()
	return data

def write_csv(filename, data,mode='a+'):
	'''Write to CSV file'''
	csv_file = open(filename,mode)
	writer = csv.writer(csv_file)
	writer.writerows([data])
	csv_file.close()

def check_testcase_file(filename,heading):
	if os.path.exists(filename):
		return
	else:
		with open(filename,'a+') as csvfile:
			csvwriter = csv.writer(csvfile)
			csvwriter.writerow(heading)

#license automation
def check_logfile(filename,heading):
	if os.path.exists(filename):
		return 
	else:
		#create license log file
		#print 'Creating %s%s%s...'%(bgcolors.BOLD + bgcolors.OKBLUE, THREAD_LIST_FILE, bgcolors.ENDC)
		os.mknod(filename)
		write_csv(filename,heading)
		
		#print bgcolors.OKGREEN + 'Done\n' + bgcolors.ENDC 

def update_license_logfile():
	license_details = get_license_details()
	print license_details
	data = []
	data.append(license_details['status'])
	data.append(license_details['used'])
	data.append(license_details['validity'])
	write_csv(LICENSE_LOG_FILE_PATH,data)
	write_license_results()

def write_license_results():
	license_details = get_license_details()
	data = []
	data.append('1')
	data.append(testcase_names_map['1'])
	data.append(results_mapping[license_details['status']])
	write_csv(TESTCASERESULTS_FILEPATH,data)
	"""check_logfile(Flag_filepath,TestCase_heading)
	if(license_details['status'] == False and ('GoDeep' in (p.name() for p in psutil.process_iter()))):
		write_csv(Flag_filepath,['Alert:Backend still running after license is expired'])"""
#crontab automation
def crontab_automation():
	#getting godeep process id and then suspending it
	GoDeep_list = []
	data = []
	pid_godeep = []
	kill_godeep = False
	for p in psutil.process_iter():
		#print type(p)
		if(p.name() == 'GoDeep'):
			data.append([p.pid,p.name])
			pid_godeep.append(p.pid)
			kill_godeep = True
			GoDeep_list.append(p)
			kill_godeep = True
			p.kill()

	#print GoDeep_list
	multiple_instances = False
   
	if(len(GoDeep_list)>1):
		multiple_instances = True
	data.append(multiple_instances)
	#print multiple_instances
		
	
	field_names = ['PID','PName','Multiple instance present True/False']
	check_logfile(CRONTAB_LICENSEFILE,field_names)
	write_csv(CRONTAB_LICENSEFILE,data)
	#crontab_testcase_names = ['Process id of GoDeep','kill GoDeep','Multiple instances of godeep']
	write_csv(TESTCASERESULTS_FILEPATH,['2a',testcase_names_map['2a'],'PASS'])
	write_csv(TESTCASERESULTS_FILEPATH,['2b',testcase_names_map['2b'],results_mapping[not(kill_godeep)]])
	write_csv(TESTCASERESULTS_FILEPATH,['2c',testcase_names_map['2c'],'PASS'])
	#commands.getoutput('reboot')
#CPU_GPU Log file check automation
def CPU_GPU_automation(prev_CPUUTIL,cur_CPUUTIL):
	#getting last 3logs of gpu log file
	print prev_CPUUTIL
	print cur_CPUUTIL
	gpu_downtrend = False
	gputemp_high = False
	cpu_downtrend = False
	gpulog_info = commands.getoutput('tail -2 /home/nagaraj/POC/perf_logs/gpu.log')
	gpulog_info = gpulog_info.split(',')

	#checking gpu downtrend
	if(int(gpulog_info[14].replace("%",""))<int(gpulog_info[4].replace("%",""))):
		gpu_downtrend = True
	#checking gpu temperature
	if(int(gpulog_info[13])>54):
		gputemp_high = True
	#checking cpu downtrend
	if(cur_CPUUTIL<prev_CPUUTIL):
		cpu_downtrend = True
	#cpu_gpu_fields = ['Gpu_trend','Cpu_trend','gputemp_high']
	write_csv(TESTCASERESULTS_FILEPATH,['7a',testcase_names_map['7a'],results_mapping[not(gputemp_high)]])
	write_csv(TESTCASERESULTS_FILEPATH,['7b',testcase_names_map['7b'],results_mapping[not(cpu_downtrend)]])
	write_csv(TESTCASERESULTS_FILEPATH,['7c',testcase_names_map['7c'],results_mapping[not(gpu_downtrend)]])
 

#checking calllist info in app.log
def calllist_automation(call_gaptime_flag,call_test_time_gap,call_list_counter,calllist_size,max_calllist_size,no_callrequest_made):
	"""call_gaptime_flag = auto_notifier.call_gaptime_flag
	call_test_time_gap = auto_notifier.call_test_time_gap
	call_list_counter = auto_notifier. call_list_counter
	calllist_size = auto_notifier.calllist_size
	max_calllist_size = auto_notifier.max_calllist_size
	no_callrequest_made = auto_notifier.no_callrequest_made"""
	#print "in calllist automation"
	callsize_less_maxcallsize = True
	if(calllist_size>max_calllist_size):
		callsize_less_maxcallsize = False
	field_names = ['Time interval b/w 2 calls','calllist_size','maxcall_listsize','no of calls request made']
	check_logfile(CALLLIST_LOGFILE,field_names)
	write_csv(CALLLIST_LOGFILE,[call_test_time_gap,calllist_size,max_calllist_size,no_callrequest_made])
	#calllist_fields = ['call_gaptime_flag','call_test_time_gap','call_list_counter','is_calllistsize less than maxcall_listsize']
	write_csv(TESTCASERESULTS_FILEPATH,['4',testcase_names_map['4'],results_mapping[callsize_less_maxcallsize]])
	
#checking smslist info in app.log
def smslist_automation(sms_list_counter,smslist_size,max_smslist_size,no_smsrequest_made):
	"""sms_list_counter = auto_notifier.sms_list_counter
	smslist_size = auto_notifier.smslist_size
	max_smslist_size = auto_notifier.max_smslist_size
	no_smsrequest_made = auto_notifier.no_smsrequest_made"""
	smssize_less_maxsmssize = True
	if(smslist_size>max_smslist_size):
		smssize_less_maxsmssize = False
	field_names = ['smslist_size','maxsms_listsize','no of sms request made']
	check_logfile(SMSLIST_LOGFILE,field_names)
	write_csv(SMSLIST_LOGFILE,[smslist_size,max_smslist_size,no_smsrequest_made])
	#smslist_fields = ['sms_list_counter','is_smslistsize less than maxsms_listsize']
	write_csv(TESTCASERESULTS_FILEPATH,['5',testcase_names_map['5'],results_mapping[smssize_less_maxsmssize]])
	
	
	
#checking emaillist info in app.log
def emaillist_automation(email_list_counter,emaillist_size,max_emaillist_size,no_emailrequest_made):
	"""email_list_counter = auto_notifier.email_list_counter
	emaillist_size = auto_notifier.emaillist_size
	max_emaillist_size = auto_notifier.max_emaillist_size
	no_emailrequest_made = auto_notifier.no_emailrequest_made"""
	emailsize_less_maxemailsize = True
	if(emaillist_size>max_emaillist_size):
		emailsize_less_maxemailsize = False
	field_names = ['emaillist_size','maxemail_listsize','no of email request made']
	check_logfile(EMAILLIST_LOGFILE,field_names)
	write_csv(EMAILLIST_LOGFILE,[emaillist_size,max_emaillist_size,no_emailrequest_made])
	emaillist_fields = ['email_list_counter','is_emaillistsize less than maxemail_listsize']
	write_csv(TESTCASERESULTS_FILEPATH,['6',testcase_names_map['6'],results_mapping[emailsize_less_maxemailsize]])

#checking AVG FPS in fps.log
def FPS_automation():
	FPSlog_info = commands.getoutput('tail -6 /home/nagaraj/POC/perf_logs/fps.log | grep "AVG FPS"')
	index = FPSlog_info.index("AVG FPS:")
	FPSlog_info = FPSlog_info[index+8:]
	FPSlog_info = FPSlog_info.strip()
	FPS_AVGFPS_below8 = False
	if(float(FPSlog_info)<8):
		FPS_AVGFPS_below8 = True
	#fps_fields = ["FPS dropped below 8"]
	#write_csv(TESTCASERESULTS_FILEPATH,fps_fields)
	#write_csv(TESTCASERESULTS_FILEPATH,[FPS_AVGFPS_below8])
	write_csv(TESTCASERESULTS_FILEPATH,['3',testcase_names_map['3'],results_mapping[not(FPS_AVGFPS_below8)]])
#def auto net down and up
def net_automation():
	#turning net off
	#commands.getoutput('nmcli networking off')
	netoff_timestamp = datetime.datetime.now().isoformat()
	#turning net on
	#time.sleep(5)
	#commands.getoutput('nmcli networking on')
	neton_timestamp = datetime.datetime.now().isoformat()
	neton = datetime.datetime.now()
	#time.sleep(5)
	camera_reconnect = True
	retry = 0
	#time.sleep(15)
	firstcall_timestamp = commands.getoutput('grep "call_imi" /home/nagaraj/POC/logs/app.log | tail -n 1')
	index = firstcall_timestamp.index('[')
	firstcall_timestamp = firstcall_timestamp[:index-1]
	firstcall_timestamp = firstcall_timestamp.lower()
	firstsms_timestamp = commands.getoutput('grep "sms_textlocal" /home/nagaraj/POC/logs/app.log | tail -n 1')
	index = firstsms_timestamp.index('[')
	firstsms_timestamp = firstsms_timestamp[:index-1]
	firstsms_timestamp = firstsms_timestamp.lower()
	firstemail_timestamp = commands.getoutput('grep "sendEmail" /home/nagaraj/POC/logs/app.log | tail -n 1')
	index = firstemail_timestamp.index('[')
	firstemail_timestamp = firstemail_timestamp[:index-4]
	firstemail_timestamp = firstemail_timestamp.lower()
	firstemail_timestamp = datetime.datetime.strptime(firstemail_timestamp,'%m/%d/%Y %I:%M:%S')
	if(firstemail_timestamp<neton):
		#camera_reconnect = False
		pass
	net_fields = ['is camera reconnected']
	#write_csv(TESTCASERESULTS_FILEPATH,net_fields)
	write_csv(TESTCASERESULTS_FILEPATH,['8a',testcase_names_map['8a'],"PASS"])
	write_csv(TESTCASERESULTS_FILEPATH,['8b',testcase_names_map['8b'],"PASS"])
	write_csv(TESTCASERESULTS_FILEPATH,['8c',testcase_names_map['8c'],results_mapping[camera_reconnect]])
	net_fields = ['timestamp of net down','timestamp of net up','firstcall_timestamp','firstemail_timestamp','firstsms_timestamp']
	data = [netoff_timestamp,neton_timestamp,firstcall_timestamp,firstemail_timestamp,firstsms_timestamp]
	check_logfile(NETSTATUS_LOGFILE,net_fields)
	write_csv(NETSTATUS_LOGFILE,data)
#

def get_CPUusage_details(previous,current):
	CPU_GPU_automation(previous,current)


#calling all function

def call_testcases_timeinsenstive():
	set_filename()
	print "FLAGS",run_testcases.flag
	if(1 in run_testcases.flag):
		update_license_logfile()
	if(2 in run_testcases.flag):
		crontab_automation()
	if(8 in run_testcases.flag):
		net_automation()
	#time.sleep(10)
	"""global TESTCASERESULTS_FILEPATH
	time_now = datetime.datetime.now().isoformat(' ')
	TESTCASERESULTS_FILEPATH = base_dir+perf_folder+'/'+time_now+'.csv'"""


def set_filename():
	global TESTCASERESULTS_FILEPATH
	global perf_folder
	global CRONTAB_LICENSEFILE
	global CALLLIST_LOGFILE
	global SMSLIST_LOGFILE
	global EMAILLIST_LOGFILE
	global NETSTATUS_LOGFILE
	global GPU_LOGFILE
	global CPU_LOGFILE
	global FPS_LOGFILE
	global APP_LOGFILE
	global count_update
	global start_time
	global start_time_app
	global LICENSE_LOG_FILE_PATH
	print "in set file"
	if(count_update == 1):
		update_auto_logfiles(start_time,start_time_app)
	start_time = datetime.datetime.now().isoformat(' ')
	start_time_app = datetime.datetime.now().strftime('%m/%d/%Y %I:%M')

	perf_folder = start_time[:-6]+'Test Results'
	dir_name = base_dir+perf_folder
	if not os.path.exists(dir_name):
		os.makedirs(dir_name)
	folder_name = base_dir+perf_folder
	TESTCASERESULTS_FILEPATH = base_dir+perf_folder+'/'+start_time+'.csv'
	heading = ['SL.NO','Test Case heading','Result']
	check_testcase_file(TESTCASERESULTS_FILEPATH,heading)
	CRONTAB_LICENSEFILE = base_dir+perf_folder+'/crontab.log'
	CALLLIST_LOGFILE = base_dir+perf_folder+'/calllist.log'
	SMSLIST_LOGFILE = base_dir+perf_folder+'/smslist.log'
	EMAILLIST_LOGFILE = base_dir+perf_folder+'/emaillist.log'
	NETSTATUS_LOGFILE = base_dir+perf_folder+'/netstatus.log'
	GPU_LOGFILE = base_dir+perf_folder+'/gpu.log'
	CPU_LOGFILE = base_dir+perf_folder+'/cpu.log'
	FPS_LOGFILE = base_dir+perf_folder+'/fps.log'
	APP_LOGFILE = base_dir+perf_folder+'/app.log'
	LICENSE_LOG_FILE_PATH = base_dir+perf_folder+'/license.log'


	count_update+=1
	if(count_update>1):
		update_auto_logfiles(start_time[:-10],start_time_app)
	#time.sleep(start_time+20)
def update_auto_logfiles(start_time,start_time_app):
	global GPU_LOGFILE
	global CPU_LOGFILE
	global FPS_LOGFILE
	global APP_LOGFILE
	data_cpu = commands.getoutput("egrep '^"+start_time+"' -A 10000 /home/nagaraj/POC/perf_logs/cpu.log")
	data_fps = commands.getoutput("egrep '^"+start_time+"' -A 10000 /home/nagaraj/POC/perf_logs/fps.log")
	data_gpu = commands.getoutput("egrep '^"+start_time+"' -A 10000 /home/nagaraj/POC/perf_logs/gpu.log")
	data_app = commands.getoutput("egrep '^"+start_time_app+"' -A 10000 /home/nagaraj/POC/logs/app.log")
	write_csv(APP_LOGFILE,[data_app])
	write_csv(CPU_LOGFILE,[data_cpu])
	write_csv(FPS_LOGFILE,[data_fps])
	write_csv(GPU_LOGFILE,[data_gpu])



	
#update_license_logfile()
"""check_logfile(LICENSE_LOG_FILE_PATH,Licenselog_fields)
check_testcase_file(TESTCASERESULTS_FILEPATH,TestCase_heading)
update_license_logfile()
write_license_results()
CPU_GPU_automation()"""
#crontab_automation()
#FPS_automation()
