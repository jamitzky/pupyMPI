#!/usr/bin/env python
# encoding: utf-8
"""
collective.py - collection of collective tests inspired by Intel MPI Benchmark (IMB)

Created by Jan Wiberg on 2009-08-13.
"""

import comm_info as ci
import common
from mpi import constants

# meta_has_meta = True
# meta_separate_communicator = False
# meta_requires_data_ranks_adjunct = False
# meta_min_processes = 4
# meta_min_data = 4

meta_size_array = (1,8,1024) # just to test if this works at all
#meta_size_array = (1,2,4,8,32,64,128,512,1024,4096,16384,32768, 65536) # should go to 4mb

def test_Bcast(size, iteration_schedule = None):
    def Bcast(data, max_iterations):
        """docstring for Bcast"""
        root = 0
        for r in max_iterations:
            my_data = data if ci.rank == root else None # probably superfluous
            ci.communicator.bcast(root, data)
            
            root += 1
            root = root % ci.num_procs

          # FIXME error and defect handling 
          # TODO note the error below in categorizing
                # CHK_DIFF("Allgather",c_info, (char*)bc_buf+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs, ...

    # end of test
    
    data = common.gen_testset(size)
    max_iterations = ci.get_iter_single(iteration_schedule, size)
    ci.synchronize_processes()

    t1 = ci.clock_function()

    # do magic
    Bcast(data, max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)/len(max_iterations) 

    return time
    
def test_Allgather(size, iteration_schedule = None):
    def Allgather(data, datalen, max_iterations):
        """docstring for Allgather"""
        for r in max_iterations:
            # TODO check if allgather verifies that the jth block size is modulo size 
            ci.communicator.allgather(data[ci.rank:ci.rank+size], size, size) # FIXME allgatherv signature likely to change 

            # FIXME defect detection and error handling

    # end of test
    data = common.gen_testset(size)*ci.num_procs
    max_iterations = ci.get_iter_single(iteration_schedule, size)
    ci.synchronize_processes()

    t1 = ci.clock_function()
    
    # do magic
    Allgather(data, size, max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)/len(max_iterations) 

    return time

    
def Allgatherv():
    pass
    
def Alltoall():
    pass
    
def Alltoallv():
    pass

def Scatter():
    pass

def Scatterv():
    pass

def Gather():
    pass

def Gatherv():
    pass

def Reduce():
    pass

def Reduce_scatter():
    pass

def Allreduce():
    pass

def test_Barrier(size, iteration_schedule = None):
    def Barrier(max_iterations):
        """docstring for Barrier"""
        for r in max_iterations:
            ci.communicator.barrier()
    # end of test
    
    max_iterations = ci.get_iter_single(iteration_schedule, size)
    ci.synchronize_processes()

    t1 = ci.clock_function()

    # do magic
    barrier(max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)/len(max_iterations) 

    return time