#!/usr/bin/env python2.6
# meta-description: Test if barriers work and do so tightly
# meta-expectedresult: 0
# meta-minprocesses: 8
# meta-max_runtime: 100

# Simple pupympi program to test barriers
# processes repeatedly barrier, pausing with varying intervals
# if test goes well nothing hangs and many barrier calls are not a problem

# NOTE: This test takes about 45 seconds with 8 processes and only 10 iterations.
# This is a bit much to include in the runtests suite.
# We might want to think of some other way to test synchronization with barriers
# for long runs.

from mpi import MPI

import time
import random


mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

random.seed(rank) # let's all be individuals
i = 10

while i > 0:
    mpi.MPI_COMM_WORLD.barrier()

    #print "rank: %i, i:%i - between barriers" % (rank,i)
        
    r = random.randint(0,2)
    time.sleep(r)
    i -= 1
    
    mpi.MPI_COMM_WORLD.barrier()
    
# Close the sockets down nicely
mpi.finalize()
