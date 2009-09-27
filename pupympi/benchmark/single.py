#!/usr/bin/env python
# encoding: utf-8
"""
single.py - collection of single/point2point tests inspired by Intel MPI Benchmark (IMB)

Created by Jan Wiberg on 2009-08-13.
Copyright (c) 2009 __MyCompanyName__. All rights reserved.
"""

import sys
import os
import comm_info as c_info
import common

def test_PingPing(size, iteration_schedule = None):
    print "test_PingPing ",size
    s_tag = 1
    r_tag = s_tag if c_info.select_tag else common.MPI_ANY_TAG
    dest = -1
    if c_info.rank == c_info.pair0:
        dest = c_info.pair1
    elif c_info.rank == c_info.pair1:
        dest = c_info.pair0
    
    source = dest if c_info.select_source else common.MPI_ANY_SOURCE 
    for b in xrange(common.N_BARR):
        mpi.barrier(c_info.communicator)

    t1 = c_info.communicator.Wtime()
    data = gen_testset(size)

    # TODO actual test!
    for r in xrange(iteration_schedule[size] if iteration_schedule is not None else 1000):
        # FIXME error handling for all statements
        mpi.isend(dest, data, common.MPI_ANY_TAG, c_info.communicator)
        recv_data = mpi.recv(dest, MPI_ANY_TAG, c_info.communicator)
        # FIXME ierr = MPI_Wait(&request, &stat);
  	    
        # TODO: check for defects

          # CHK_DIFF("PingPing",c_info, (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
          #           0, size, size, asize,
          #           put, 0, ITERATIONS->n_sample, i,
          #           dest, &defect);

    t2 = c_info.communicator.Wtime()
    time=(t2 - t1)/1000 # FIXME iter_sched
        
    return time
    
def test_PingPong(size, iteration_schedule = None):
    print "test_PingPong"

