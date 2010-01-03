#!/usr/bin/env python
# encoding: utf-8
"""
special.py - collection of special tests
"""

import comm_info as ci
from mpi import constants

meta_has_meta = True
meta_processes_required = 2
meta_min_processes = 2
meta_result_configuration = "special"
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
    8192: 1000
}
    
def test_ThreadSaturation(size, max_iterations):
    def PingPing(s_tag, r_tag, source, dest, data, max_iterations):
        for r in xrange(max_iterations):
            request = ci.communicator.isend(dest, data)
            recv_data = ci.communicator.recv(source)
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

    