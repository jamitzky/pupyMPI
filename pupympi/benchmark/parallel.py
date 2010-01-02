#!/usr/bin/env python
# encoding: utf-8
"""
parallel.py - collection of parallel tests inspired by Intel MPI Benchmark (IMB)

Created by Jan Wiberg on 2009-08-13.
"""

import comm_info as ci
from mpi import constants


meta_has_meta = True
meta_processes_required = -1
meta_min_processes = 2
meta_schedule = {
    0: 1000,
    1: 1000,
    2: 1000,
    4: 1000,
    8: 1000,
    16: 1000,
    32: 1000,
    64: 1000,
    128: 1000,
    256: 1000,
    512: 1000,
    1024: 1000,
    2048: 1000,
    4096: 1000,
    8192: 1000,
    16384: 1000,
    32768: 1000,
    65536: 640,
    131072: 320,
    262144: 160,
    524288: 80,
    1048576: 40,
    2097152: 20,
    4194304: 10
}

def test_Sendrecv(size, max_iterations):
    def get_srcdest_chained(): # this fails for c=2, obviously. Since we want to run for 8 or 32, no reason to fix
        assert ci.num_procs > 2 # 
        dest   = (ci.rank + 1) % ci.num_procs
        source = (ci.rank + ci.num_procs-1) % ci.num_procs
        return (source, dest)

    def Sendrecv(s_tag, r_tag, source, dest, data, max_iterations):        
        #print "%s -> [%s] -> %s" % (source, ci.rank, dest)
        for r in xrange(max_iterations):
            recvdata = ci.communicator.sendrecv(data, dest, s_tag, source, r_tag)
    # end of test

    (s_tag, r_tag) = ci.get_tags_single()
    data = ci.data[0:size]
    ci.synchronize_processes()

    (source, dest) = get_srcdest_chained()        
    t1 = ci.clock_function()
    
    # do magic
    Sendrecv(s_tag, r_tag, source, dest, data, max_iterations)
    
    t2 = ci.clock_function()
    time = (t2 - t1)

    return time

def test_Exchange(size, max_iterations):
    def get_leftright_chained():
        if ci.rank < ci.num_procs-1:
            right = ci.rank+1
        if ci.rank > 0:
            left = ci.rank-1

        if ci.rank == ci.num_procs-1:
            right = 0
        if  ci.rank == 0:
            left = ci.num_procs-1 
            
        return (left, right)
            
    def Exchange(s_tag, r_tag, left, right, data, max_iterations):        
        for r in xrange(max_iterations):
            ci.communicator.isend(right, data, s_tag)
            ci.communicator.isend(left, data, s_tag)
            leftdata = ci.communicator.recv(left, r_tag)
            rightdata = ci.communicator.recv(right, r_tag)

    # end of test
    (s_tag, r_tag) = ci.get_tags_single()
    data = ci.data[0:size]
    ci.synchronize_processes()

    (left, right) = get_leftright_chained()        

    t1 = ci.clock_function()

    # do magic
    Exchange(s_tag, r_tag, left, right, data, max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)

    return time
 
 # multi versions    
     # Multi-PingPong 
     # Multi-PingPing
     # Multi-Sendrecv 
     # Multi-Exchange

