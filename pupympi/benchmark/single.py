#!/usr/bin/env python
# encoding: utf-8
"""
single.py - collection of single/point2point tests inspired by Intel MPI Benchmark (IMB)

Created by Jan Wiberg on 2009-08-13.
"""

import comm_info as ci
import common
from mpi import constants

def setup_single_test(size, single_test, iteration_schedule = None):
    (s_tag, r_tag) = ci.get_tags_single()
    (source, dest) = ci.get_dest_single() # source for purposes of recv, rank-relative
    data = common.gen_testset(size)
    max_iterations = ci.get_iter_single(iteration_schedule, size)

    ci.synchronize_processes()

    t1 = ci.clock_function()
    
    # do magic
    single_test(s_tag, r_tag, source, dest, data, max_iterations)
    
    t2 = ci.clock_function()
    time = (t2 - t1)/len(max_iterations) 

    return time
    

def exif_PingPing(size, iteration_schedule = None):
    return 0 # FIXME
    
    (s_tag, r_tag) = ci.get_tags_single()
    (source, dest) = ci.get_dest_single()
    data = common.gen_testset(size)
    max_iterations = ci.get_iter_single(iteration_schedule, size)

    ci.barrier()

    t1 = ci.clock_function()

    for r in xrange(iteration_schedule[size] if iteration_schedule is not None else 1000):
        # FIXME error handling for all statements
        ci.communicator.isend(dest, data)
        recv_data = ci.communicator.recv(source)
        # FIXME ierr = MPI_Wait(&request, &stat);
  	    
        # TODO: check for defects

          # CHK_DIFF("PingPing",ci, (char*)ci->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
          #           0, size, size, asize,
          #           put, 0, ITERATIONS->n_sample, i,
          #           dest, &defect);

    t2 = ci.communicator.Wtime()
    time = (t2 - t1)/1000 # FIXME iter_sched
        
    return time
    
def test_PingPong(s_tag, r_tag, source, dest, data, max_iterations):
    for r in max_iterations:
        print "rank %s iteration %s, source %s, dest %s, datalen %s" % (ci.rank, r, source, dest, len(data))
        if ci.rank == ci.pair0: 
            ci.communicator.send(dest, data, s_tag)
            recv = ci.communicator.recv(source, r_tag)
            # FIXME Verify data if enabled        
        elif ci.rank == ci.pair1:
            recv = ci.communicator.recv(source, r_tag)
            ci.communicator.send(dest, data, s_tag)
            # FIXME Verify data if enabled
        else: 
            raise Exception("Broken state")
        
