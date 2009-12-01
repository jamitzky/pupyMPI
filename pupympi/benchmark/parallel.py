#!/usr/bin/env python
# encoding: utf-8
"""
parallel.py - collection of parallel tests inspired by Intel MPI Benchmark (IMB)

Created by Jan Wiberg on 2009-08-13.
"""

import comm_info as ci
import common
from mpi import constants

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
def test_Sendrecv(size):
    def get_srcdest_chained():
        dest   = (ci.rank + 1) % ci.num_procs
        source = (ci.rank + ci.num_procs-1) % ci.num_procs
        return (source, dest)

    def Sendrecv(s_tag, r_tag, source, dest, data, max_iterations):        
        #print "%s -> [%s] -> %s" % (source, ci.rank, dest)
        for r in max_iterations:
            recvdata = ci.communicator.sendrecv(data, dest, s_tag, source, r_tag)
            # FIXME: check for defects
    # end of test

    (s_tag, r_tag) = ci.get_tags_single()
    data = common.gen_testset(size)
    max_iterations = ci.get_iter_single(iteration_schedule, size)
    ci.synchronize_processes()

    (source, dest) = get_srcdest_chained()        

    t1 = ci.clock_function()
    
    # do magic
    Sendrecv(s_tag, r_tag, source, dest, data, max_iterations)
    
    t2 = ci.clock_function()
    time = (t2 - t1)/len(max_iterations) 

    return time

def test_Exchange(size):
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
        for r in max_iterations:
            # FIXME: check for defects
            ci.communicator.isend(right, data, s_tag)
            ci.communicator.isend(left, data, s_tag)
            leftdata = ci.communicator.recv(left, r_tag)
            rightdata = ci.communicator.recv(right, r_tag)

    # end of test
    (s_tag, r_tag) = ci.get_tags_single()
    data = common.gen_testset(size)
    max_iterations = ci.get_iter_single(iteration_schedule, size)
    ci.synchronize_processes()

    (left, right) = get_leftright_chained()        

    t1 = ci.clock_function()

    # do magic
    Exchange(s_tag, r_tag, left, right, data, max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)/len(max_iterations) 

    return time
 
 # multi versions    
     # Multi-PingPong 
     # Multi-PingPing
     # Multi-Sendrecv 
     # Multi-Exchange

