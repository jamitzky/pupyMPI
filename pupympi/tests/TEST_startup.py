#!/usr/bin/env python2.6

from mpi import MPI
import time

print "before init"

mpi = MPI.initialize()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

print "Started process process %d / %d" % (rank, size)

time.sleep(7)

# Close the sockets down nicely
mpi.finalize()
