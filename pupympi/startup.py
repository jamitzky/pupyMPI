#!/usr/bin/env python2.6

import mpi, time

mpi = mpi.MPI()

rank = mpi.rank()
size = mpi.size()

time.sleep(size-rank)

print "Closing process process %d of %d after %d seconds sleep" % (rank, size, size-rank)

