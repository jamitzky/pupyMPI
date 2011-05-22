#!/usr/bin/env python
"""
parallel.py

pupyMPI parallelized version of Monte Carlo Pi approximator

This is an example of an application with very little communication. Only a
barrier to start with and a gather to sum up results.
"""

import math, random, sys, time
from mpi import MPI


def approximate(rank,iterations):
    num_in = 0
    
    # algorithm
    # Seed with rank to get deterministic results that are not using the same random.uniform-space for multiple processes
    random.seed(rank) 
    for i in xrange(iterations):
        x = random.uniform(0,1)
        y = random.uniform(0,1)
        if x*x + y*y <= 1:
            num_in += 1
        
    return num_in


if __name__ == "__main__":
    # MPI setup
    mpi = MPI()
    comm = mpi.MPI_COMM_WORLD
    rank = comm.rank()
    size = comm.size()
    
    # regular setup
    if ( len(sys.argv) != 2 ):
        print "Usage: " + sys.argv[0] + " sample_number"
        mpi.finalize()
        sys.exit(0)
    
    iterations = int(sys.argv[1])
    local_iterations = iterations / size
    
    t1 = time.time()

    # Run algo
    hits = approximate(rank,local_iterations)

    # distribute    
    global_hits = comm.reduce(hits,sum)
    
    print "Rank %s: hits: %s, iterations:%i, time %s" % (rank, global_hits, iterations, time.time()-t1)

    # rank 0 gathers and displays
    if rank == 0:
        ratio = float(global_hits) / float(iterations)
        approximate_pi = 4 * ratio
    
        print "Within circle: " + str(iterations)
        print "Total hits: " + str(global_hits)
        print "Ratio: " + str(ratio)
        print "Python's Internal Pi: " + str(math.pi)
        print "*** Approx. Pi: " + str(approximate_pi) + " ***"
        print "Discrepancy: " + str(math.pi - approximate_pi)
        print "Internal time: " + str(time.time() - t1)

    mpi.finalize()

