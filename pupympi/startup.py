#!/usr/bin/env python2.6

import mpi, time, sys

mpi = mpi.MPI()

rank = mpi.rank()
size = mpi.size()

print sys.path

time.sleep(max(2,size-rank))

print "Closing process process %d of %d after %d seconds sleep" % (rank, size, size-rank)

# Close the sockets down nicely
mpi.finalize()
