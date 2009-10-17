#!/usr/bin/env python2.6
# meta-description: allreduce, first computes factorial of mpi_size, then uses builtin max to find slowest process.
# meta-expectedresult: 0

from mpi import MPI
from mpi.operations import prod

def fact(n):
    if n == 0:
        return 1
    else:
        return n * fact(n-1)
    
mpi = MPI()
from datetime import datetime
n = datetime.now()
# We start n processes, and try to calculate n!
rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()
dist_fact = mpi.MPI_COMM_WORLD.allreduce(rank+1, prod)

time_taken = datetime.now()-n

print "I'm rank %d and I also got the result %d. So cool. Took %s" % (rank, dist_fact, time_taken)

max_time  = mpi.MPI_COMM_WORLD.allreduce(time_taken, max)

if rank == 0:
    print "Maximum time for the first allreduce was", max_time

assert fact(size) == dist_fact

mpi.finalize()
