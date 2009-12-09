#!/usr/bin/env python2.6
# meta-description: Test if barriers work. 
# meta-expectedresult: 0
# meta-minprocesses: 11

# Simple pupympi program to test barrier
# All ranks synchronize at barrier
# Rank 0 sleeps for 5 seconds before joining the next barrier
# all ranks should see at least a 4 second interval between t1 and t2 caused
# by waiting for rank 0 at the second barrier.

from mpi import MPI

import time
from datetime import datetime

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

#print "%s: I am the process with rank %d of %d processes, now barrier'ing" % (datetime.now(), rank, size)
mpi.MPI_COMM_WORLD.barrier()

t1 = time.time()

if rank == 0:
    time.sleep(5)

mpi.MPI_COMM_WORLD.barrier()

t2 = time.time()

assert (t2 - t1) > 5
#print "%s: I am the process with rank %d of %d processes, past barrier" % (datetime.now(), rank, size)

# Close the sockets down nicely
mpi.finalize()
