#
# Copyright 2010 Rune Bromer, Frederik Hantho and Jan Wiberg
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
import sys
import threading, inspect
from time import time
from collections import deque
from mpi import constants

STATE_USER = 1
STATE_MPI_COMM = 2
STATE_MPI_COLLECTIVE = 3
STATE_MPI_WAIT = 4

def trace_event(frame, event, arg):
    global p_prevthread, p_lock

    with p_lock:
        ct = threading.currentThread()
        pt = p_prevthread

        try:
            p_stack = ct.p_stack
        except AttributeError:
            ct.p_stack = deque()
            p_stack = ct.p_stack

        try:
            ts = p_ttime[ct.name]
        except KeyError:
            p_ttime[ct.name] = {"t0": time(), "ttot": 0}
            ts = p_ttime[ct.name]

        # Thread context change
        if pt and pt != ct:
            diff = time() - p_ttime[pt.name]["t0"]
            p_ttime[pt.name]["ttot"] += diff
            p_ttime[ct.name]["t0"] = time()

        if ct.name == "MainThread":
            if event == "call":
                code = frame.f_code
                print "[%s] CALL   %s.%s" % (time(), code.co_filename, code.co_name)
            if event == "c_call":
                print "[%s] C_CALL %s" % (time(), arg)
            if event == "return":
                code = frame.f_code
                print "[%s] RET    %s.%s" % (time(), code.co_filename, code.co_name)
            if event == "c_return":
                print "[%s] C_RET  %s" % (time(), arg)
            if event == "c_exception":
                pass

        p_prevthread = threading.currentThread()

        return None

def start():
    global p_stats, p_start_time, p_lock, p_ttime, p_prevthread
    p_stats = {}
    p_ttime = {}
    p_start_time = time()
    p_lock = threading.Lock()
    p_prevthread = None
    
    print "Starting built-in profiler"
    threading.setprofile(trace_event)
    sys.setprofile(trace_event)

def stop():
    print "Stopping built-in profiler"
    threading.setprofile(None)
    sys.setprofile(None)

def dump_stats(filename):
    print "Dumping stats."
    
    f = open(filename, "w")
    ttot = 0
    for name in p_ttime:
        ttot += p_ttime[name]["ttot"]
        print >>f, "-- %-12s: %.2f sec" % (name, p_ttime[name]["ttot"])

    print >>f, "Total time: %.2f sec" % (ttot)
    f.close()

