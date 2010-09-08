#!/usr/bin/env python2.6
# encoding: utf-8
#
# Copyright 2010 Rune Bromer, Asser Schrøder Femø, Frederik Hantho and Jan Wiberg
# This file is part of pupyMPI.
# 
# pupyMPI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
# 
# pupyMPI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License 2
# along with pupyMPI.  If not, see <http://www.gnu.org/licenses/>.
#
"""
runtests.py - test runner for pupympi
"""

import sys
from optparse import OptionParser
import subprocess
import os
from threading import Thread
import time

help_message = '''
Read the source, lazy bum.
'''
# Allow the user to import mpi without specifying PYTHONPATH in the environment
mpirunpath  = os.path.dirname(os.path.abspath(__file__)) # Path to mpirun.py
mpipath,rest = os.path.split(mpirunpath) # separate out the bin dir (dir above is the target)
sys.path.append(mpipath) # Set PYTHONPATH

# settings
TEST_EXECUTION_TIME_GRANULARITY = 0.2 # sleep time between checking if process is dead (also determines gran. of execution time, obviously)
TEST_MAX_RUNTIME = 15 # max time in seconds that one single test may take, if not otherwise specified


HEADER = '\033[95m'
OKBLACK ='\033[30m'
OKOFFWHITE = '\033[90m'
OKRED = '\033[31m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'

# latex_output = None

def output_console(text, color = None, newline = True, block = "", output=True):
    """Adds one block/line of output to console"""
    out = ""
    if color:
        out += color
    out += text
    if color:
        out += ENDC
    if newline:
        out += "\n\r"
    if output:
        sys.stdout.write(out)
        sys.stdout.flush() 
    return out

def output_console_nocolor(text, color = None, newline = True, block = "", output=True):
    """Adds one block/line of output to console, no colors for the yuppie types"""
    out = ""
    out += text
    if newline:
        out += "\n\r"
    if output:
        sys.stdout.write(out)
        sys.stdout.flush() 
    return out

    
# def output_latex(test):
#     """Adds one block/line of output as latex output"""
#     global latex_output
# 
#     
#     description = test.meta["description"].replace("_", "\\_") if "description" in test.meta else ""
#     testname = test.test.replace("TEST_", "").replace("_", "\\_").replace(".py", "")
#     result = "success" if test.returncode == test.expectedresult and not test.killed else "failed"
#     
#     latex_output.write("%s & %s & %s & %s \\\\ \n" % (testname, test.processes, result, description))
            
output = output_console


path = os.path.dirname(os.path.abspath(__file__)) 
class RunTest(Thread):

    #cmd = "bin/mpirun.py --process-io=localfile -q -c PROCESSES_REQUIRED --startup-method=STARTUP_METHOD -v LOG_VERBOSITY -l PRIMARY_LOG_TEST_TRUNC_NAME tests/TEST_NAME"
    #cmd = "bin/mpirun.py --single-communication-thread --process-io=localfile -q -c PROCESSES_REQUIRED --startup-method=STARTUP_METHOD -v LOG_VERBOSITY -l PRIMARY_LOG_TEST_TRUNC_NAME tests/TEST_NAME"
    # With dynamic socket pool
    cmd = "bin/mpirun.py --disable-full-network-startup SOCKET_POOL_SIZE --process-io=localfile -q -c PROCESSES_REQUIRED --startup-method=STARTUP_METHOD -v LOG_VERBOSITY -l PRIMARY_LOG_TEST_TRUNC_NAME tests/TEST_NAME"
    #cmd = "bin/mpirun.py --single-communication-thread --disable-full-network-startup --process-io=localfile -q -c PROCESSES_REQUIRED --startup-method=STARTUP_METHOD -v LOG_VERBOSITY -l PRIMARY_LOG_TEST_TRUNC_NAME tests/TEST_NAME"

    def __init__(self, test, number, primary_log, options, test_meta_data):
        Thread.__init__(self)
        self.test = test
        self.meta = test_meta_data
        self.primary_log = primary_log
        self.processes = test_meta_data.get("minprocesses", options.np)
        self.expectedresult = int(test_meta_data.get("expectedresult", 0))
        self.cmd = self.cmd.replace("PROCESSES_REQUIRED", str(self.processes))
        self.cmd = self.cmd.replace("LOG_VERBOSITY", str(options.verbosity))
        self.cmd = self.cmd.replace("PRIMARY_LOG", primary_log)
        self.cmd = self.cmd.replace("TEST_TRUNC_NAME", test[test.find("_")+1:test.rfind(".")])
        self.cmd = self.cmd.replace("TEST_NAME", test)
        self.cmd = self.cmd.replace("STARTUP_METHOD", options.startup_method)
        
        # If socket pool size is specified in meta description we add appropriate parameter
        if "socket-pool-size" in test_meta_data:
            self.cmd = self.cmd.replace("SOCKET_POOL_SIZE", "--socket-pool-size "+test_meta_data["socket-pool-size"])
        else:
            self.cmd = self.cmd.replace("SOCKET_POOL_SIZE", "")
            #self.cmd = self.cmd.replace("SOCKET_POOL_SIZE", "--socket-pool-size 20")
        
        # Adds testswitches if used
        if options.socket_poll_method:
            self.cmd += " --socket-poll-method=" + options.socket_poll_method
        # Adds user arguments to the test if there are meta descriptions for it. 
        if "userargs" in test_meta_data:
            self.cmd += " -- " + test_meta_data['userargs']
        
        output( "Launching(%i) %s: " % (number, self.cmd), newline=False)
        self.process = subprocess.Popen(self.cmd.split())
        self.killed = False
        self.time_to_get_result_or_die = int(test_meta_data["max_runtime"]) if "max_runtime" in test_meta_data else TEST_MAX_RUNTIME

    def run(self):
        """runs the testthread, logs realtime'ish results and kills the subprocess if it takes too long."""
        self.start = time.time()
        while time.time() < (self.start + self.time_to_get_result_or_die): # Limit execution time
            if self.process.poll() is not None: # Has the process stopped running?
                break
            time.sleep(TEST_EXECUTION_TIME_GRANULARITY)

        self.executiontime = time.time() - self.start 
        #print "Time to kill ",str(self.process)
        if self.process.poll() is None: # Still running means it hit time limit
            self.killed = True
            output( "Timed out" )
            self.process.terminate() # Try SIGTERM
            time.sleep(0.5)
            if self.process.poll() is None:
                self.process.kill() # SIGTERM did not do it, now we SIGKILL
        elif self.process.returncode != self.expectedresult:
            output("Failed", OKRED)
        else:
            output("OK")  
        #print self.process.communicate()
        self.returncode = self.process.returncode

def get_testnames(skipto = 0):
    """returns a list of files that match our 'official' requirement to qualify as a pupympi test"""
    tests = sorted([f for f in os.listdir("tests/") if f.startswith("TEST_")])
    
    if skipto > 0: # skip some tests from the beginning
        tests = tests[skipto:]
    elif skipto < 0: # skip some tests from the end
        tests = tests[:skipto]
    
    return tests

    
def _status_str(ret, expres):
    """helper function to write human friendly status string"""
    if ret == expres:
        return output("ok", newline=False, output=False)
    elif ret == -9 or ret == -15:
        return output("Timed Out", newline=False, output=False)
    else:
        return output("FAIL: %s" % ret, color=OKRED,newline=False, output=False)
        
def format_output(threads):
    """prints the final output in purty colors, and logs to latex for report inclusion"""
    testcounter = 1
    total_time = 0
    odd = False
    output("    NAME\t\t\t\tEXECUTION TIME (sec)\tKILLED\tRETURNED") 
    output("--------------------------------------------------------------------------------")
    for thread in threads:
        total_time += thread.executiontime
        output("%3i %-40s\t\t%4s\t%s\t%s" % (testcounter, \
                                            thread.test, \
                                            round(thread.executiontime, 1), \
                                            "KILLED" if thread.killed else "no", \
                                            _status_str(thread.returncode, thread.expectedresult)),
                                            color=OKOFFWHITE if odd else OKBLACK,
                                            block="Results table console")                                                    
        odd = True if odd == False else False
        # output_latex(thread)
        testcounter += 1
        
    output( "\nTotal execution time: %ss" % (round(total_time, 1)))

def combine_logs(logfile_prefix):
    """Logs are initially split to ease debugging. This function combines them, and deletes the original."""
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

def get_test_data(test):
    """loads test metadata and filename"""
    with open("tests/"+test) as testfile:
        meta = {}
        for lines in testfile.readlines():
            if not lines.startswith("#"):
                break
                
            if lines.startswith("# meta-"):
                meta[lines[7:lines.find(":")]] = lines[lines.find(":")+1:].strip()
        
        return meta            

def run_tests(test_files, options):
    """for each test in tests directory, run the test"""
    threadlist = []
    logfile_prefix = time.strftime("testrun-%m%d%H%M%S")
    
    # with open("testrun.tex", "w") as latex:
    #     global latex_output
    #     latex_output = latex
    
    testcounter = 1
    # We run tests sequentially since many of them are rather hefty and may
    # interfere with others. Also breakage can lead to side effects and so
    # non-breaking tests may appear to break when in fact the cause is another
    # test running at the same time
    for test in test_files:
        t = RunTest(test, testcounter, logfile_prefix, options, get_test_data(test))
        threadlist.append(t)
        t.start()
        t.join()
        testcounter += 1

    format_output(threadlist)
    combine_logs(logfile_prefix)
    
class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main():
    usage = 'usage: %prog [options]'
    parser = OptionParser(usage=usage, version="Pupympi version 0.8")
    parser.add_option('-v', '--verbosity', dest='verbosity', type='int', default=1, help='How much information should be logged and printed to the screen. Should be an integer between 1 and 3, defaults to 1.')
    parser.add_option('-c', '--np', dest='np', default=2, type='int', help='The number of processes to start.')
    parser.add_option('--startup-method', dest='startup_method', default="ssh", metavar='method', help='How the processes should be started. Choose between ssh and popen. Defaults to ssh')
    parser.add_option('--remote-python', dest='remote_python', default="python", metavar='method', help='Path to the python executable on the remote side')
    parser.add_option('--socket-poll-method', dest='socket_poll_method', default=False, help="Specify which socket polling method to use. Available methods are epoll (Linux only), kqueue (*BSD only), poll (most UNIX variants) and select (all operating systems). Default behaviour is to attempt to use either epoll or kqueue depending on the platform, then fall back to poll and finally select.")

    parser.add_option('-r', '--runtests-from', dest='skipto', type='int', default=0, help='What number test (alphabetically sorted) to start testing from. Negative values leave out tests from the end as with slicing.')

    # _ is args
    options, _ = parser.parse_args()

    run_tests( get_testnames(options.skipto), options )

if __name__ == "__main__":
    sys.exit(main())
