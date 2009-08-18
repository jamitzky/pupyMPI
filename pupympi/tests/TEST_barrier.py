#!/usr/bin/env python2.6

# Simple pupympi program to test barrier

import mpi
from sys import stderr


mpi = mpi.MPI()

rank = mpi.MPI_COMM_WORLD.rank()

size = mpi.MPI_COMM_WORLD.size()

print "I am the process with rank %d of %d processes, now barrier'ing" % (rank, size)
mpi.barrier(mpi.MPI_COMM_WORLD)
print "I am the process with rank %d of %d processes, past barrier" % (rank, size)

# Close the sockets down nicely
mpi.finalize()
