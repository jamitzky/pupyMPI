#!/usr/bin/env python2.6

from mpi import MPI
import time

mpi = MPI.initialize()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

print "Started process process %d / %d" % (rank, size)

time.sleep(5)
time.sleep(5)

# Close the sockets down nicely
mpi.finalize()
