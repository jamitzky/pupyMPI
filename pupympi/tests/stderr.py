#!/usr/bin/env python2.6

import mpi, time

mpi = mpi.MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

print "Started process process %d / %d" % (rank, size)

if rank == 0:
    try:
        1/0
    except Exception,e :
        import sys
        sys.stderr.write("Der er sket en fejl")

    print "Completing process process %d / %d" % (rank, size)
else:
    1/0

# Close the sockets down nicely
mpi.finalize()
