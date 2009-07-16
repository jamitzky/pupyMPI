#!/usr/bin/env python2.6

# Simple pupympi program to test startup of processes and assigning/reporting of ranks

import mpi


mpi = mpi.MPI()

rank = mpi.rank()
size = mpi.size()

print "I am the process with rank %d of %d processes" % (rank, size)

# Close the sockets down nicely
mpi.finalize()