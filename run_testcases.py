import auto_testcases
import time
import sched
import commands
import os
s = sched.scheduler(time.time, time.sleep)
flag = []	
def run_timeinsentive():
	s.enter(auto_testcases.interval_time,1,auto_testcases.call_testcases_timeinsenstive,())
	s.run()
	run_timeinsentive()

def run_all():
	print "yess"
	s.enter(auto_testcases.interval_time, 1,auto_testcases.call_testcases_timeinsenstive,())
	s.run()
	run_all()

def run_timesentive():
	s.enter(auto_testcases.interval_time, 1,auto_testcases.set_filename,())
	s.run()
	run_timesentive()

def one():
	s.enter(auto_testcases.interval_time, 1,auto_testcases.update_license_logfile,())
	s.run()
	one()

def two():
	s.enter(auto_testcases.interval_time, 1,auto_testcases.crontab_automation,())
	s.run()
	two()

def three():
	s.enter(auto_testcases.interval_time, 1,auto_testcases.FPS_automation,())
	s.run()
	three()

def four():
	s.enter(auto_testcases.interval_time, 1,auto_testcases.set_filename,())
	s.run()
	four()
	
def five():
	s.enter(auto_testcases.interval_time, 1,auto_testcases.set_filename,())
	s.run()
	five()
	
def six():
	s.enter(auto_testcases.interval_time, 1,auto_testcases.set_filename,())
	s.run()
	six()

def seven():
	s.enter(auto_testcases.interval_time, 1,auto_testcases.set_filename,())
	s.run()
	seven()

def eight():
	s.enter(auto_testcases.interval_time, 1,auto_testcases.net_automation,())
	s.run()
	eight()


def display():
	global choice
	global flag
	flag = [0]*10
	choice_user = auto_testcases.read_csv('/home/nagaraj/POC/UserMenu.csv')
	filters = []
	for choice in choice_user[1:10]:
		filters.append(choice[2])

	choice_user = filters
	print choice_user
	filters = []
	for i in range(len(choice_user)):
		if(choice_user[i] == '1'):
			filters.append(i+1)

	choice_user = filters
	flag = choice_user
	print choice_user
	if(len(choice_user)>1 and ((1 in choice_user and 2 in choice_user) or (1 in choice_user and 8 in choice_user) or (2 in choice_user and 8 in choice_user))):
		run_timeinsentive()
	elif(9 not in choice_user):
		run_all()
	else:
		choice_user = [1,2,3,4,5,6,7,8,9,10]
		flag = choice_user
		run_all()
	print choice_user
	print "hey bbb"
	return

	for choice in choice_user:
		if(choice == 1):
			flag[choice-1] = 1
			one()

		elif(choice == 2):
			flag[choice-1] = 1
			two()
		elif(choice == 3):
			flag[choice-1] = 1
			three()
		elif(choice == 4):
			flag[choice-1] = 1
			four()
		elif(choice == 5):
			flag[choice-1] = 1
			five()
		elif(choice == 6):
			flag[choice-1] = 1
			six()
		elif(choice == 7):
			flag[choice-1] = 1
			seven()
		elif(choice == 8):
			flag[choice-1] = 1
			eight()

		elif(choice == 9):
			for i in range(9):
				flag[i] = 1
			run_all()


#schedule_run()
#auto_testcases.call_testcases_timesensitive()
#starttime = time.time()
#time.sleep(20.0 - ((time.time() - starttime) % 60.0))
