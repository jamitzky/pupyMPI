#!/usr/bin/env python2.6

# Simple pupympi program to test basic communication between to processes

import mpi, time


mpi = mpi.MPI()

rank = mpi.rank()
size = mpi.size()

time.sleep(max(2,size-rank))

print "Closing process %d of %d after %d seconds sleep" % (rank, size, size-rank)

# Close the sockets down nicely
mpi.finalize()
