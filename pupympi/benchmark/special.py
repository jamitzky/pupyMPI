#!/usr/bin/env python
# encoding: utf-8
"""
special.py - collection of special tests
"""

import comm_info as ci
from mpi import constants

meta_has_meta = True
meta_processes_required = 8
meta_min_processes = 2
meta_result_configuration = "special"
meta_schedule = {
    0: 10000,
    1: 10000,
    2: 10000,
    4: 10000,
    8: 10000,
    16: 10000,
    32: 10000,
    64: 10000,
    128: 10000,
    256: 10000,
    512: 10000,
    1024: 10000,
    2048: 10000,
    4096: 10000,
    8192: 10000
}
    
# def test_ThreadSaturationPing(size, max_iterations):
#     def PingPing(s_tag, r_tag, source, dest, data, max_iterations):
#         for r in xrange(max_iterations):
#             request = ci.communicator.isend(dest, data)
#             recv_data = ci.communicator.recv(source)
#             request.wait()        
#     # end of test
#     
#     (s_tag, r_tag) = ci.get_tags_single()
#     (source, dest) = ci.get_srcdest_paired() # source for purposes of recv, rank-relative
#     data = ci.data[0:size]
#     ci.synchronize_processes()
# 
#     t1 = ci.clock_function()
# 
#     # do magic
#     PingPing(s_tag, r_tag, source, dest, data, max_iterations)
# 
#     t2 = ci.clock_function()
#     time = (t2 - t1)
# 
#     return time

def test_ThreadSaturationExchange(size, max_iterations):
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
    
def test_ThreadSaturationBcast(size, max_iterations):
    def Bcast(data, max_iterations):
        """docstring for Bcast"""
        root = 0
        for r in xrange(max_iterations):
            my_data = data if ci.rank == root else "" # NOTE: probably superflous, discuss with Rune
            ci.communicator.bcast(my_data, root)
            # Switch root
            root = (root +1) % ci.num_procs
    # end of test


    ci.synchronize_processes()

    t1 = ci.clock_function()

    # Doit
    Bcast(ci.data[:size], max_iterations)

    t2 = ci.clock_function()

    time = (t2 - t1)
    return time    
    