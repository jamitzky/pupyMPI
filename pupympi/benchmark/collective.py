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
def test_Bcast(size):
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
    
def test_Allgather(size):
    def Allgather(data, datalen, max_iterations):
        """docstring for Allgather"""
        for r in max_iterations:
            # TODO check if allgather verifies that the jth block size is modulo size 
            ci.communicator.allgather(data[ci.rank:ci.rank+size], size, size) # FIXME allgather signature may change 

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

    
def test_Allgatherv(size):
    def Allgatherv(data, datalen, max_iterations):
        """docstring for Allgather"""
        for r in max_iterations:
            # TODO check if allgather verifies that the jth block size is modulo size 
            ci.communicator.allgatherv(data[ci.rank:ci.rank+size], size, ci.rdispl) # FIXME allgatherv signature may change 
            # ierr = MPI_Allgatherv((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
            #                       s_num,c_info->s_data_type,
            #                       (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
            #                       c_info->reccnt,c_info->rdispl,
            #                       c_info->r_data_type,
            #                       c_info->communicator);

            # FIXME defect detection and error handling

    # end of test
    data = common.gen_testset(size)*ci.num_procs
    max_iterations = ci.get_iter_single(iteration_schedule, size)
    ci.rdispl = 1 # FIXME not necessarily best
    ci.synchronize_processes()

    t1 = ci.clock_function()
    
    # do magic
    Allgatherv(data, size, max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)/len(max_iterations) 

    return time
    
def test_Alltoall(size):
    def Alltoall(data, datalen, max_iterations):
        """docstring for Alltoall"""
        for r in max_iterations:
            ci.communicator.alltoall(data[ci.rank:ci.rank+size], ci.sndcnt, data, ci.reccnt)
                  #             ierr = MPI_Alltoall((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
                  #                                 s_num,c_info->s_data_type,
                  # (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
                  #                                 r_num,c_info->r_data_type,
                  # c_info->communicator);
            # FIXME defect detection and error handling

    # end of test
    data = common.gen_testset(size)*ci.num_procs
    max_iterations = ci.get_iter_single(iteration_schedule, size)
    ci.rdispl = 1 # FIXME not necessarily best
    ci.synchronize_processes()

    t1 = ci.clock_function()
    
    # do magic
    Allgatherv(data, size, max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)/len(max_iterations) 

    return time 
       
def test_Alltoallv(size):
    def Alltoallv(data, datalen, max_iterations):
        pass
    # end of test
    pass

def test_Scatter(size):
    def Scatter(data, datalen, max_iterations):
        pass
    # end of test
    pass

def test_Scatterv(size):
    def Scatterv(data, datalen, max_iterations):
        pass
    # end of test
    pass

def test_Gather(size):
    def Gather(data, datalen, max_iterations):
        pass
    # end of test
    pass

def test_Gatherv(size):
    def Gatherv(data, datalen, max_iterations):
        pass
    # end of test
    pass

def test_Reduce(size):
    def Reduce(data, datalen, max_iterations):
        """docstring for Reduce"""
        for r in max_iterations:
            pass
            
                #           ierr = MPI_Reduce((char*)c_info->s_buffer+i%ITERATIONS->s_cache_iter*ITERATIONS->s_offs,
                #                             (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs,
                #                             s_num,
                # c_info->red_data_type,c_info->op_type,
                # i1,c_info->communicator);
                #           MPI_ERRHAND(ierr);
                # 
                #             #ifdef CHECK
                #              if( c_info->rank == i1 )
                #              {
                #                   CHK_DIFF("Reduce",c_info, (char*)c_info->r_buffer+i%ITERATIONS->r_cache_iter*ITERATIONS->r_offs, 0,
                #                            size, size, asize, 
                #                            put, 0, ITERATIONS->n_sample, i,
                #                            -1, &defect);
                #              }
                #             #endif
                #         /*  CHANGE THE ROOT NODE */
                #         i1=(++i1)%c_info->num_procs;
    # end of test

    # end of test
    data = common.gen_testset(size)*ci.num_procs
    max_iterations = ci.get_iter_single(iteration_schedule, size)
    ci.rdispl = 1 # FIXME not necessarily best
    ci.synchronize_processes()

    t1 = ci.clock_function()
    
    # do magic
    Reduce(data, size, max_iterations)

    t2 = ci.clock_function()
    time = (t2 - t1)/len(max_iterations) 

    return time    


def test_Reduce_scatter(size):
    def Reduce_scatter(data, datalen, max_iterations):
        pass
    # end of test
    pass

def test_Allreduce(size):
    def Allreduce(data, datalen, max_iterations):
        pass
    # end of test
    pass

def test_Barrier(size):
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