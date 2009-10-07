#!/usr/bin/env python
# encoding: utf-8
"""
parallel.py - collection of parallel tests inspired by Intel MPI Benchmark (IMB)

Created by Jan Wiberg on 2009-08-13.
"""

import sys
import os

def do_test(size, parallel_test, iteration_schedule = None):
    """
    Sets up environment, times and runs test
    """
    (s_tag, r_tag) = ci.get_tags_single()
    (source, dest) = ci.get_dest_single() # source for purposes of recv, rank-relative
    data = common.gen_testset(size)
    max_iterations = ci.get_iter_single(iteration_schedule, size)

    ci.synchronize_processes()

    t1 = ci.clock_function()
    
    # do magic
    parallel_test(s_tag, r_tag, source, dest, data, max_iterations)
    
    t2 = ci.clock_function()
    time = (t2 - t1)/len(max_iterations) 

    return time
    
def Sendrecv():
    pass
    
def Exchange():
    pass
    
 
 # multi versions    
     # Multi-PingPong 
     # Multi-PingPing
     # Multi-Sendrecv 
     # Multi-Exchange

