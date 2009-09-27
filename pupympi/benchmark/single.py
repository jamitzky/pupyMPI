#!/usr/bin/env python
# encoding: utf-8
"""
single.py - collection of single/point2point tests inspired by Intel MPI Benchmark (IMB)

Created by Jan Wiberg on 2009-08-13.
"""

import comm_info as c_info
import common
from mpi import constants

def test_PingPing(size, iteration_schedule = None):
    return 0 # FIXME
    
    (s_tag, r_tag) = c_info.get_tags_single()
    (source, dest) = c_info.get_dest_single()
    data = common.gen_testset(size)
    max_iterations = c_info.get_iter_single(iteration_schedule, size)

    c_info.barrier()

    t1 = c_info.communicator.Wtime()

    for r in xrange(iteration_schedule[size] if iteration_schedule is not None else 1000):
        # FIXME error handling for all statements
        c_info.communicator.isend(dest, data)
        recv_data = c_info.communicator.recv(source)
        # FIXME ierr = MPI_Wait(&request, &stat);
  	    
        # TODO: check for defects

          # CHK_DIFF("PingPing",c_info, (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
          #           0, size, size, asize,
          #           put, 0, ITERATIONS->n_sample, i,
          #           dest, &defect);

    t2 = c_info.communicator.Wtime()
    time = (t2 - t1)/1000 # FIXME iter_sched
        
    return time
    
def test_PingPong(size, iteration_schedule = None):
    return 0.0
    print "Into test_PingPong"
    (s_tag, r_tag) = c_info.get_tags_single()
    print "s_tag %s, r_tag %s" % (s_tag, r_tag)
    (source, dest) = c_info.get_dest_single() # source for purposes of recv
    print "source %s, dest %s" % (source, dest)
    data = common.gen_testset(size)
    max_iterations = c_info.get_iter_single(iteration_schedule, size)
    print "Data length %s, max_iters %s" % (len(data), max_iterations)

    c_info.barrier()
    iterations = 0

    t1 = c_info.communicator.Wtime()    
    if c_info.rank is c_info.pair0: 
        print "I am rank %s congruent with pair0, my source,dest is %s,%s, s_tag %s, r_tag %s" % (c_info.rank, source, dest, s_tag, r_tag)
        for r in max_iterations:
            iterations += 1
            c_info.communicator.send(dest, data, s_tag)
            print "%s done sending" % c_info.rank
            recv = c_info.communicator.recv(source, r_tag)
            # FIXME Verify data if enabled
        
    elif c_info.rank is c_info.pair1:
        print "I am rank %s congruent with pair1, my source,dest is %s,%s" % (c_info.rank, source, dest)
        for r in max_iterations:
            iterations += 1
            recv = c_info.communicator.recv(source, r_tag)
            print "%s done recv" % c_info.rank
            c_info.communicator.send(dest, data, s_tag)
            # FIXME Verify data if enabled
    else: 
        raise Exception("Broken state")
        
    t2 = c_info.communicator.Wtime()
    time = (t2 - t1)/iterations 

    return time
        

def test_Simple_PingPong(size, iteration_schedule = None):
    data = ''.join(["a"] * size)
    f = open("/tmp/rank%s.log" % c_info.rank, "w")
    c_info.barrier()
    iterations = 0

    t1 = c_info.communicator.Wtime()    
    if c_info.rank is 0: 
        while iterations < 5:
            iterations += 1
            c_info.communicator.send(1, data, 1)
            # print "%s: %s done sending" % (iterations, c_info.rank)
            recv = c_info.communicator.recv(1, 1)
            # print "%s: %s done receiving %s" % (iterations, c_info.rank, "str(recv)")
            # FIXME Verify data if enabled
            f.write("Iteration %s completed for rank %s\n" % (iterations, c_info.rank)) 
            f.flush()
        f.write( "Done for rank 0\n")
    elif c_info.rank is 1:
        while iterations < 5:
            iterations += 1
            recv = c_info.communicator.recv(0, 1)
            # print "%s, %s done recv: %s" % (iterations, c_info.rank," str(recv)")
            c_info.communicator.send(0, data, 1)
            # print "%s: %s done sending" % (iterations, c_info.rank)
            # FIXME Verify data if enabled
            f.write( "Iteration %s completed for rank %s\n" % (iterations, c_info.rank))
            f.flush()
        f.write( "Done for rank 1\n")
    else: 
        raise Exception("Broken state")


    t2 = c_info.communicator.Wtime()
    time = (t2 - t1) 

    f.write( "Timings were %s for data length %s'n" % (time, len(data)))
    f.flush()
    f.close()
    return time


