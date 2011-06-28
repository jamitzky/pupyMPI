#!/usr/bin/env python
# encoding: utf-8
"""
collective.py - collection of collective tests inspired by Intel MPI Benchmark (IMB)
"""
#from mpi.collective.operations import MPI_max
from mpi.collective.operations import MPI_sum

import comm_info as ci

meta_requires_data_ranks_adjunct = False
meta_processes_required = 2
meta_enlist_all = True

meta_schedule = {
    0: 100,
    1: 100,
    2: 100,
    4: 100,
    8: 100,
    16: 100,
    32: 100,
    64: 100,
    128: 100,
    256: 100,
    512: 100,
    1024: 100,
    2048: 100,
    4096: 100,
    8192: 100,
    16384: 100,
    32768: 100,
    65536: 64,
    131072: 32,
    262144: 16,
    524288: 8,
    1048576: 8,
    2097152: 8,
    4194304: 8
}
def test_Bcast(size, max_iterations):
    comm = ci.communicator
    num_procs = ci.num_procs

    def Bcast(data, max_iterations):
        """docstring for Bcast"""
        root = 0
        for _ in xrange(max_iterations):
            comm.bcast(data, root)

            # Switch root
            root = (root +1) % num_procs

    # end of test
    ci.synchronize_processes()

    t1 = ci.clock_function()

    # Doit
    Bcast(ci.data[:size], max_iterations)

    t2 = ci.clock_function()

    time = (t2 - t1)
    return time

def test_Allgather(size, max_iterations):
    comm = ci.communicator

    def Allgather(data, max_iterations):
        """docstring for Allgather"""
        for _ in xrange(max_iterations):
            comm.allgather( data )
    # end of test

    ci.synchronize_processes()

    t1 = ci.clock_function()

    # do magic
    Allgather(ci.data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1

    return time


def test_Alltoall(size, max_iterations):
    comm = ci.communicator
    def Alltoall(data, max_iterations):
        """docstring for Alltoall"""
        for _ in xrange(max_iterations):
            comm.alltoall(data)
        # end of test

    # Slice the data to the size needed
    dataslice = ci.data[:(size*ci.num_procs)]
    ci.synchronize_processes()
    t1 = ci.clock_function()

    # do magic
    Alltoall(dataslice, max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time

def test_Scatter(size, max_iterations):
    rank = ci.rank
    num_procs = ci.num_procs
    comm = ci.communicator

    data = ci.data[:(size*num_procs)]

    def Scatter(data, max_iterations):
        current_root = 0
        for _ in xrange(max_iterations):
            comm.scatter(data, current_root)

            # Switch root
            current_root = (current_root +1) % num_procs
    # end of test

    # scatter makes no sense for size < 1
    if not size > 0:
        return None

    ci.synchronize_processes()
    t1 = ci.clock_function()

    # do magic
    Scatter(data, max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time

def test_Gather(size, max_iterations):
    comm = ci.communicator
    num_procs = ci.num_procs

    def Gather(data, max_iterations):
        current_root = 0
        for _ in xrange(max_iterations):
            comm.gather(data, current_root)
            # Switch root
            current_root = (current_root +1) % num_procs
    # end of test

    ci.synchronize_processes()
    t1 = ci.clock_function()

    # do magic
    Gather(ci.data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time

def test_Reduce(size, max_iterations):
    comm = ci.communicator
    num_procs = ci.num_procs

    def Reduce(data, max_iterations):
        """docstring for Reduce"""
        current_root = 0
        for _ in xrange(max_iterations):
            # For the reduce operator we use pupyMPI's built-in max
            comm.reduce(data, MPI_sum, current_root)
            # Switch root
            current_root = (current_root +1) % num_procs
    # end of test

    # reduce makes no sense for size < 1
    if not size > 0:
        return None

    ci.synchronize_processes()
    t1 = ci.clock_function()
    
    # do magic
    Reduce(ci.reduce_data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time

def test_Allreduce(size, max_iterations):
    comm = ci.communicator

    def Allreduce(data, max_iterations):
        for _ in xrange(max_iterations):
            # For the reduce operator we use pupyMPI's built-in max
            comm.allreduce(data, MPI_sum)
    # end of test

    # allreduce makes no sense for size < 1
    if not size > 0:
        return None

    ci.synchronize_processes()
    t1 = ci.clock_function()

    # do magic
    Allreduce(ci.reduce_data[:size], max_iterations)

    t2 = ci.clock_function()
    time = t2 - t1
    return time

def test_Barrier(size, max_iterations):
    comm = ci.communicator
    def Barrier(max_iterations):
        """docstring for Barrier"""
        for _ in xrange(max_iterations):
            comm.barrier()
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

