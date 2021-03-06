#!/usr/bin/env python
# encoding: utf-8
"""
single.py - collection of single/point2point tests inspired by Intel MPI Benchmark (IMB)
"""

import comm_info as ci

meta_processes_required = 2
meta_enlist_all = False


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
    
def test_PingPing(size, max_iterations):
    def PingPing(s_tag, r_tag, source, dest, data, max_iterations):
        for _ in xrange(max_iterations):
            request = ci.communicator.isend(data, dest)
            ci.communicator.recv(source)
            request.wait()  	    
    # end of test
    
    (s_tag, r_tag) = ci.get_tags_single()
    (source, dest) = ci.get_srcdest_paired() # source for purposes of recv, rank-relative
    data = ci.data[0:size]
    ci.synchronize_processes()

    t1 = ci.clock_function()

    # do magic
    PingPing(s_tag, r_tag, source, dest, data, max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)

    return time

    
def test_PingPong(size, max_iterations):
    def PingPong(s_tag, r_tag, source, dest, data, max_iterations):
        for _ in xrange(max_iterations):
            if ci.rank == ci.pair0: 
                ci.communicator.send(data, dest, s_tag)
                ci.communicator.recv(source, r_tag)
            elif ci.rank == ci.pair1:
                ci.communicator.recv(source, r_tag)
                ci.communicator.send(data, dest, s_tag)
            else: 
                raise Exception("Broken state")
    # end of test
    
    (s_tag, r_tag) = ci.get_tags_single()
    (source, dest) = ci.get_srcdest_paired() # source for purposes of recv, rank-relative
    data = ci.data[0:size]

    ci.synchronize_processes()

    t1 = ci.clock_function()

    # do magic
    PingPong(s_tag, r_tag, source, dest, data, max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)

    return time

