#!/usr/bin/env python
# encoding: utf-8
"""
collective.py - collection of collective tests inspired by Intel MPI Benchmark (IMB)
"""
from mpi.operations import MPI_list_max

import comm_info as ci

meta_has_meta = True
meta_requires_data_ranks_adjunct = False
meta_processes_required = 4
meta_enlist_all = True

meta_schedule = {
    0: 10,
    1: 10,
    2: 10,
    4: 10,
    8: 10,
    16: 10,
    32: 10,
    64: 10,
    128: 10,
    256: 10,
    512: 10,
    1024: 10,
    2048: 10,
    4096: 10,
    8192: 10,
    16384: 10,
    32768: 10,
    65536: 5,
    131072: 5,
    262144: 5,
    524288: 5,
    1048576: 5,
    2097152: 5,
    4194304: 5
}
def test_Bcast(size, max_iterations):
    def Bcast(data, max_iterations):
        """docstring for Bcast"""
        root = 0
        for _ in xrange(max_iterations):
            ci.communicator.bcast(data, root)
            
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

# Goes to max 16384 on the cluster with 8 procs
def test_Allgather(size, max_iterations):
    def Allgather(data, max_iterations):
        """docstring for Allgather"""
        for _ in xrange(max_iterations):
            ci.communicator.allgather( data )
    # end of test
    
    # Allgather is not valid for size < num_procs
    if size < ci.num_procs:
        return -42
    
    ci.synchronize_processes()

    t1 = ci.clock_function()
    
    # do magic
    Allgather(ci.data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1

    return time

    
def test_Alltoall(size, max_iterations):
    def Alltoall(data, max_iterations):
        """docstring for Alltoall"""
        for _ in xrange(max_iterations):
            ci.communicator.alltoall(data)
        # end of test

    # Alltoall is not valid for size < numprocs
    if size < ci.num_procs:
        return -42
    
    #Prepack data into lists for nicer iteration
    # We send size/numprocs data to each process
    chunksize = size/ci.num_procs
    # each distinct chunk goes to a distinct process
    datalist = [ ci.data[(x*chunksize):(x*chunksize)+chunksize] for x in range(ci.num_procs) ]
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Alltoall(datalist, max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time 
       
def test_Scatter(size, max_iterations):
    def Scatter(data, max_iterations):
        current_root = 0
        for _ in xrange(max_iterations):
            my_data = data if ci.rank == current_root else None # NOTE: probably superflous, discuss with Rune
            ci.communicator.scatter(my_data, current_root)
            
            # Switch root
            current_root = (current_root +1) % ci.num_procs
    # end of test
    
    # Scatter is not valid for size < numprocs
    if size < ci.num_procs:
        return -42
    
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Scatter(ci.data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time 

def test_Gather(size, max_iterations):
    def Gather(data, max_iterations):
        current_root = 0
        for _ in xrange(max_iterations):
            ci.communicator.gather(data, current_root)            
            # Switch root
            current_root = (current_root +1) % ci.num_procs
    # end of test
    
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Gather(ci.data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time

def test_Reduce(size, max_iterations):
    def Reduce(data, max_iterations):
        """docstring for Reduce"""
        current_root = 0
        for _ in xrange(max_iterations):
            # For the reduce operator we use pupyMPI's built-in max over lists
            ci.communicator.reduce(data, MPI_list_max, current_root)            
            # Switch root
            current_root = (current_root +1) % ci.num_procs
    # end of test
    
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Reduce(ci.data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time

def test_Allreduce(size, max_iterations):
    def Allreduce(data, max_iterations):
        for _ in xrange(max_iterations):
            # For the allreduce operator we use Python built-in max
            ci.communicator.allreduce(data, max)            

    # end of test
    
    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Allreduce(ci.data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time
 
def test_Barrier(size, max_iterations):
    def Barrier(max_iterations):
        """docstring for Barrier"""
        for _ in xrange(max_iterations):
            ci.communicator.barrier()
    # end of test

    if size is not 0: 
        return None # We don't care about barrier for increasing sizes
    
    ci.synchronize_processes()
    t1 = ci.clock_function()

    # do magic
    Barrier(max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time
