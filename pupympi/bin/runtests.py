#!/usr/bin/env python2.6
# encoding: utf-8
"""
runtests.py

Created by Jan Wiberg on 2009-08-11.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
import getopt
import subprocess
import os
from threading import Thread
import time

help_message = '''
Read the source, lazy bum.
'''

# settings
RUN_COUNT = 2 # MPI processes started...tests can use no more than this number
TEST_MAX_RUNTIME = 4 # max time in seconds that one single test may take.
LOG_VERBOSITY = 3

class RunTest(Thread):
    cmd = "python bin/mpirun.py -q -c RUN_COUNT -v LOG_VERBOSITY -l PRIMARY_LOG_TEST_TRUNC_NAME tests/TEST_NAME"
    def __init__(self, test, primary_log):
        Thread.__init__(self)
        self.test = test
        self.primary_log = primary_log
        self.cmd = self.cmd.replace("RUN_COUNT", str(RUN_COUNT))
        self.cmd = self.cmd.replace("LOG_VERBOSITY", str(LOG_VERBOSITY))
        self.cmd = self.cmd.replace("PRIMARY_LOG", primary_log)
        self.cmd = self.cmd.replace("TEST_TRUNC_NAME", test[test.find("_")+1:test.rfind(".")])
        self.cmd = self.cmd.replace("TEST_NAME", test)
        print "About to launch ",self.cmd
        self.process = subprocess.Popen(self.cmd.split(" "), stdout=subprocess.PIPE)
        self.killed = False

    def run(self):
        self.start = time.time()
        while time.time() < (self.start + TEST_MAX_RUNTIME): # hax: wait for max 10'ish seconds
            if self.process.poll() is not None:
                break
            time.sleep(0.5)

        self.executiontime = time.time() - self.start 
        #print "Time to kill ",str(self.process)
        if self.process.poll() is None:
            self.killed = True
            self.process.terminate()
            time.sleep(0.25)
            if self.process.poll() is None:
                self.process.kill()
            
        #print self.process.communicate()
        self.returncode = self.process.returncode

def get_testnames():
    return sorted([f for f in os.listdir("tests/") if f.startswith("TEST_")])
    
def format_output(threads):
    print "TEST NAME\t\t\t\t\tEXECUTION TIME(s)\tKILLED\t\tTEST RETURNCODE"
    print "-----------------------------------------------------------------------------------------------------------"
    for thread in threads:
        print "%-45s\t\t%s\t\t%s\t\t%s" % (thread.test, round(thread.executiontime,1), \
                                            thread.killed, \
                                            "%s (%s)" % ("OK" if thread.returncode == 0 else "FAILURE", thread.returncode))
        

def combine_logs(logfile_prefix):
    combined = open(logfile_prefix+".log", "w")
    counter = 0
    for log in sorted([f for f in os.listdir(".") if f.startswith(logfile_prefix+"_")]):
        counter += 1
        lf = open(log, "r")
        combined.write("LOG DETAILS FOR %s\n------------------------------------------------" % log)
        lines = lf.readlines()
        #print "About to write %s lines to %s" % (len(lines), combined)
        combined.writelines(lines)
        combined.write("\n\n")
        lf.close()
        os.remove(log)    

    combined.close()        
    print "\nCombined %d log files into %s.log" % (counter, logfile_prefix)

def run_tests(test_files):
    threadlist = []
    logfile_prefix = time.strftime("testrun-%m%d%H%M%S")
    for test in test_files:
        t = RunTest(test, logfile_prefix)
        threadlist.append(t)
        t.start()
        t.join() # run sequentially until issue #19 is fixed

    # for t in threadlist:
    #    t.join()
    #    print "all done"
    
    format_output(threadlist)
    combine_logs(logfile_prefix)
    
class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "ho:v", ["help", "output="])
        except getopt.error, msg:
            raise Usage(msg)
    
        # option processing
        for option, value in opts:
            if option == "-v":
                verbose = True
            if option in ("-h", "--help"):
                raise Usage(help_message)
            if option in ("-o", "--output"):
                output = value
    
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2

    run_tests( get_testnames() )

if __name__ == "__main__":
    sys.exit(main())