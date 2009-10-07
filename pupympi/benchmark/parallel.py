#!/usr/bin/env python
# encoding: utf-8
"""
parallel.py - collection of parallel tests inspired by Intel MPI Benchmark (IMB)

Created by Jan Wiberg on 2009-08-13.
"""

import comm_info as ci
import common
from mpi import constants

def do_test(size, parallel_test, iteration_schedule = None):
    """
    Sets up environment, times and runs test
    """
    def get_srcdest_chained():
        dest   = (ci.rank + 1) % ci.num_procs
        source = (ci.rank + ci.num_procs-1) % ci.num_procs
        return (source, dest)
    (s_tag, r_tag) = ci.get_tags_single()
    (source, dest) = get_srcdest_chained()        
    data = common.gen_testset(size)
    max_iterations = ci.get_iter_single(iteration_schedule, size)

    ci.synchronize_processes()

    t1 = ci.clock_function()
    
    # do magic
    parallel_test(s_tag, r_tag, source, dest, data, max_iterations)
    
    t2 = ci.clock_function()
    time = (t2 - t1)/len(max_iterations) 

    return time
    
def test_Sendrecv(s_tag, r_tag, source, dest, data, max_iterations):
        
    #print "%s -> [%s] -> %s" % (source, ci.rank, dest)
    
    
    
def test_Exchange(s_tag, r_tag, source, dest, data, max_iterations):
    pass
    
 
 # multi versions    
     # Multi-PingPong 
     # Multi-PingPing
     # Multi-Sendrecv 
     # Multi-Exchange

