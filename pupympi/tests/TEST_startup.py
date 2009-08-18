#!/usr/bin/env python2.6

import mpi, time

mpi = mpi.MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

import sys

print sys.argv

print "Started process process %d / %d" % (rank, size)

# Close the sockets down nicely
mpi.finalize()
