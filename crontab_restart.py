import psutil
import auto_testcases
base_dir = '/opt/godeep/'
perf_folder = 'perf_logs'
CRONTAB_LICENSEFILE = base_dir+perf_folder+'/crontab.log'
TESTCASERESULTS = perf_folder+'/testcaseresults.csv'
TESTCASERESULTS_FILEPATH = base_dir+TESTCASERESULTS
def crontab_automation():
    #getting godeep process id and then suspending it
    GoDeep_list = []
    data = []
    pid_godeep = []
    for p in psutil.process_iter():
        #print type(p)
        if(p.name() == 'GoDeep'):
            data.append([p.pid,p.name])
            pid_godeep.append(p.pid)
            GoDeep_list.append(p)

    print GoDeep_list
    multiple_instances = False
   
    if(len(GoDeep_list)>1):
        multiple_instances = True
    data.append(multiple_instances)
    print multiple_instances
        

    field_names = ['PID','PName','Multiple instance present True/False']
    auto_testcases.check_logfile(CRONTAB_LICENSEFILE,field_names)
    auto_testcases.write_csv(CRONTAB_LICENSEFILE,data)
    crontab_testcase_names = ['Process id of GoDeep','Multiple instances of godeep']
    auto_testcases.write_csv(TESTCASERESULTS_FILEPATH,crontab_testcase_names)
    auto_testcases.write_csv(TESTCASERESULTS_FILEPATH,[pid_godeep,multiple_instances])


crontab_automation()