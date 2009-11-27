#!/usr/bin/env python2.6
# meta-description: Test if barriers work. 
# meta-expectedresult: 0
# meta-minprocesses: 11

# Simple pupympi program to test barrier
# FIXME: make the test automatic

from mpi import MPI
from sys import stderr
import time
from datetime import datetime

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()

size = mpi.MPI_COMM_WORLD.size()

print "%s: I am the process with rank %d of %d processes, now barrier'ing" % (datetime.now(), rank, size)

if rank == 0:
    time.sleep(4)

mpi.MPI_COMM_WORLD.barrier()
print "%s: I am the process with rank %d of %d processes, past barrier" % (datetime.now(), rank, size)

# Close the sockets down nicely
mpi.finalize()
