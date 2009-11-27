#!/usr/bin/env python
# encoding: utf-8
"""
parallel.py - collection of parallel tests inspired by Intel MPI Benchmark (IMB)

Created by Jan Wiberg on 2009-08-13.
"""

import comm_info as ci
import common
from mpi import constants

meta_size_array = (1,8,1024) # just to test if this works at all
#meta_size_array = (1,2,4,8,32,64,128,512,1024,4096,16384,32768, 65536) # should go to 4mb

def test_Sendrecv(size, iteration_schedule = None):
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

def test_Exchange(size, iteration_schedule = None):
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

