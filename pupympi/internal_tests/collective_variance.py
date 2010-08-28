#!/usr/bin/env python2.6
"""
Test the strange variance for different datasizes when running collective benchmarks
"""
import time, array, sys
from mpi import MPI
from mpi.operations import MPI_prod,MPI_sum, MPI_avg, MPI_min, MPI_max
    
mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

max_iterations = 10 # In benchmarks this is 100
datasizes = [0,1,2,4,8,16,32,64,128,256,512,1024]


baseset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
def gen_testset(size):
    """Generates a test message byte array of asked-for size. Used for single and parallel ops.
    Current implementation is really slow - even without random.
    """

    data = array.array('b')
    for x in xrange(0, size):
        data.append(ord(baseset[x % len(baseset)])) # Fast generation of data
    return data

def test_Reduce(datasize, max_iterations):
    def Reduce(data, max_iterations):
        """docstring for Reduce"""
        current_root = 0
        for _ in xrange(max_iterations):
            # For the reduce operator we use pupyMPI's built-in max over lists
            world.reduce(data, MPI_max, current_root)            
            # Switch root
            current_root = (current_root +1) % size
    # end of test
    
    world.barrier()
    t1 = time.time()
    
    # Run the iterations
    Reduce(testdata[:datasize], max_iterations)

    t2 = time.time()
    delta = t2 - t1
    return delta

# If a particular size is specified as user argument, only that will be tested
try:
    specified_size = sys.argv[1]
    if specified_size: # Eliminate others from datasizes
        datasizes = [int(specified_size)] #NOTE: could check for integer type here
except:
    pass

testdata = gen_testset(max(datasizes))
for d in datasizes:
    res = test_Reduce(d,max_iterations)
    
    if rank==0:
        print "%i iterations in %s seconds for size:%i" % (max_iterations,res,d)


mpi.finalize()
