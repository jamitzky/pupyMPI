#!/usr/bin/env python2.6

# Simple pupympi program to test assigning/reporting of ranks and reporting of size

from sys import stderr
from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()

size = mpi.MPI_COMM_WORLD.size()

print "I am the process with rank %d of %d processes" % (rank, size)

# Close the sockets down nicely
mpi.finalize()
