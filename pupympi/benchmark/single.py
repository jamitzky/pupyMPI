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
    pass

def test_PingPing(size, iteration_schedule = None):
    return 0 # FIXME
    
    (s_tag, r_tag) = ci.get_tags_single()
    (source, dest) = ci.get_dest_single()
    data = common.gen_testset(size)
    max_iterations = ci.get_iter_single(iteration_schedule, size)

    ci.barrier()

    t1 = ci.communicator.Wtime()

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
    
def test_PingPong(size, iteration_schedule = None):
    (s_tag, r_tag) = ci.get_tags_single()
    (source, dest) = ci.get_dest_single() # source for purposes of recv, rank-relative
    data = common.gen_testset(size)
    max_iterations = ci.get_iter_single(iteration_schedule, size)

    ci.synchronize_processes()

    t1 = ci.communicator.Wtime()    
    for r in max_iterations:
        print "rank %s iteration %s, source %s, dest %s" % (ci.rank, r, source, dest)
        if ci.rank == ci.pair0: 
            print "I think im rank 0 - sending with tag %s" % s_tag
            ci.communicator.send(dest, data, s_tag)
            print "I think im rank 0 - posting receive"
            recv = ci.communicator.recv(source, r_tag)
            # FIXME Verify data if enabled        
        elif ci.rank == ci.pair1:
            print "I think im rank 1 - posting receive for tag %s" % r_tag
            recv = ci.communicator.recv(source, r_tag)
            print "I think im rank 1 - send data"            
            ci.communicator.send(dest, data, s_tag)
            # FIXME Verify data if enabled
        else: 
            raise Exception("Broken state")
    t2 = ci.communicator.Wtime()
    time = (t2 - t1)/max_iterations 

    return time
        

def test_Simple_PingPong(size, iteration_schedule = None):
    return 0.0
    data = ''.join(["a"] * size)
    f = open("/tmp/rank%s.log" % ci.rank, "w")
    ci.barrier()
    iterations = 0

    t1 = ci.communicator.Wtime()    
    if ci.rank is 0: 
        while iterations < 5:
            iterations += 1
            ci.communicator.send(1, data, 1)
            # print "%s: %s done sending" % (iterations, ci.rank)
            recv = ci.communicator.recv(1, 1)
            # print "%s: %s done receiving %s" % (iterations, ci.rank, "str(recv)")
            # FIXME Verify data if enabled
            f.write("Iteration %s completed for rank %s\n" % (iterations, ci.rank)) 
            f.flush()
        f.write( "Done for rank 0\n")
    elif ci.rank is 1:
        while iterations < 5:
            iterations += 1
            recv = ci.communicator.recv(0, 1)
            # print "%s, %s done recv: %s" % (iterations, ci.rank," str(recv)")
            ci.communicator.send(0, data, 1)
            # print "%s: %s done sending" % (iterations, ci.rank)
            # FIXME Verify data if enabled
            f.write( "Iteration %s completed for rank %s\n" % (iterations, ci.rank))
            f.flush()
        f.write( "Done for rank 1\n")
    else: 
        raise Exception("Broken state")


    t2 = ci.communicator.Wtime()
    time = (t2 - t1) 

    f.write( "Timings were %s for data length %s'n" % (time, len(data)))
    f.flush()
    f.close()
    return time


