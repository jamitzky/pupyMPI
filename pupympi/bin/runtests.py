#!/usr/bin/env python2.6
# encoding: utf-8
"""
runtests.py

Created by Jan Wiberg on 2009-08-11.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
from optparse import OptionParser, OptionGroup
import subprocess
import os
from threading import Thread
import time

help_message = '''
Read the source, lazy bum.
'''

# settings
TEST_EXECUTION_TIME_GRANULARITY = 0.2 # sleep time between checking if process is dead (also determines gran. of execution time, obviously)
TEST_MAX_RUNTIME = 15 # max time in seconds that one single test may take.


HEADER = '\033[95m'
OKBLACK ='\033[30m'
OKOFFWHITE = '\033[90m'
OKRED = '\033[31m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'


path = os.path.dirname(os.path.abspath(__file__)) 
class RunTest(Thread):
    cmd = "bin/mpirun.py -q -c RUN_COUNT --startup-method=STARTUP_METHOD --remote-python REMOTE_PYTHON -v LOG_VERBOSITY -l PRIMARY_LOG_TEST_TRUNC_NAME tests/TEST_NAME"
    def __init__(self, test, primary_log, options):
        Thread.__init__(self)
        self.test = test
        self.primary_log = primary_log
        self.cmd = self.cmd.replace("RUN_COUNT", str(options.np))
        self.cmd = self.cmd.replace("LOG_VERBOSITY", str(options.verbosity))
        self.cmd = self.cmd.replace("PRIMARY_LOG", primary_log)
        self.cmd = self.cmd.replace("TEST_TRUNC_NAME", test[test.find("_")+1:test.rfind(".")])
        self.cmd = self.cmd.replace("TEST_NAME", test)
        self.cmd = self.cmd.replace("REMOTE_PYTHON", options.remote_python)
        self.cmd = self.cmd.replace("STARTUP_METHOD", options.startup_method)
        sys.stdout.write( "Launching %s: " % self.cmd)
        sys.stdout.flush() # because python sucks
        self.process = subprocess.Popen(self.cmd.split(" "), stdout=subprocess.PIPE)
        self.killed = False

    def run(self):
        self.start = time.time()
        while time.time() < (self.start + TEST_MAX_RUNTIME): # HACK: Limit execution time
            if self.process.poll() is not None: # Has the process stopped running?
                break
            time.sleep(TEST_EXECUTION_TIME_GRANULARITY)

        self.executiontime = time.time() - self.start 
        #print "Time to kill ",str(self.process)
        if self.process.poll() is None: # Still running means it hit time limit
            self.killed = True
            print "Timed out"
            self.process.terminate() # Try SIGTERM
            time.sleep(0.25)
            if self.process.poll() is None:
                self.process.kill() # SIGTERM did not do it, now we SIGKILL
        elif self.process.returncode is not 0:
            print OKRED + "Failed" + ENDC
        else:
            print "OK"  
        #print self.process.communicate()
        self.returncode = self.process.returncode

def get_testnames():
    return sorted([f for f in os.listdir("tests/") if f.startswith("TEST_")])
    
def _status_str(ret):
    if ret == 0:
        return "ok"
    elif ret == -9 or ret == -15:
        return "Timed out"
    else:
        return OKRED + "FAILURE: " + str(ret) + ENDC
        
def format_output(threads):
    total_time = 0
    odd = False
    print "TEST NAME\t\t\t\t\tEXECUTION TIME(s)\tKILLED\t\tTEST RETURNCODE"
    print "-----------------------------------------------------------------------------------------------------------"
    for thread in threads:
        total_time += thread.executiontime
        print "%s%-45s\t\t%s\t\t%s\t\t%s%s" % (OKOFFWHITE if odd else OKBLACK, \
                                            thread.test, round(thread.executiontime, 1), \
                                            "KILLED" if thread.killed else "no", \
                                            _status_str(thread.returncode),
                                            ENDC)
        odd = True if odd == False else False
        
    print "\nTotal execution time: %ss" % (round(total_time, 1))

def combine_logs(logfile_prefix):
    combined = open(logfile_prefix+".log", "w")
    counter = 0
    for log in sorted([f for f in os.listdir(".") if f.startswith(logfile_prefix+"_")]):
        counter += 1
        lf = open(log, "r")
        combined.write("LOG DETAILS FOR %s\n------------------------------------------------\n" % log)
        lines = lf.readlines()
        #print "About to write %s lines to %s" % (len(lines), combined)
        combined.writelines(lines)
        combined.write("\n\n")
        lf.close()
        os.remove(log)    

    combined.close()        
    print "Combined %d log files into %s.log" % (counter, logfile_prefix)

def run_tests(test_files, options):
    threadlist = []
    logfile_prefix = time.strftime("testrun-%m%d%H%M%S")
    for test in test_files:
        t = RunTest(test, logfile_prefix, options)
        threadlist.append(t)
        t.start()
        t.join() # run sequentially until issue #19 is fixed
        # TODO: Issue 19 is resolved, try fixing the above

    # for t in threadlist:
    #    t.join()
    #    print "all done"
    
    format_output(threadlist)
    combine_logs(logfile_prefix)
    
class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main():
    usage = 'usage: %prog [options]'
    parser = OptionParser(usage=usage, version="Pupympi version 0.01 (dev)")
    parser.add_option('-v', '--verbosity', dest='verbosity', type='int', default=1, help='How much information should be logged and printed to the screen. Should be an integer between 1 and 3, defaults to 1.')
    parser.add_option('--startup-method', dest='startup_method', default="ssh", metavar='method', help='How the processes should be started. Choose between ssh and popen. Defaults to ssh')
    parser.add_option('-c', '--np', dest='np', default=4, type='int', help='The number of processes to start.')
    parser.add_option('--remote-python', '-r', dest='remote_python', default="python", metavar='method', help='Path to the python executable on the remote side')

    options, args = parser.parse_args()

    run_tests( get_testnames(), options )

if __name__ == "__main__":
    sys.exit(main())
