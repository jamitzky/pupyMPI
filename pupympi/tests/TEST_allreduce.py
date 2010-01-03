#!/usr/bin/env python2.6
# meta-description: allreduce, first computes factorial of mpi_size
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI
from mpi.operations import MPI_prod
from datetime import datetime

def fact(n):
    if n == 0:
        return 1
    else:
        return n * fact(n-1)
    
mpi = MPI()
world = mpi.MPI_COMM_WORLD
n = datetime.now()

# We start n processes, and try to calculate n!
rank = world.rank()
size = world.size()

dist_fact = world.allreduce(rank+1, MPI_prod)

assert fact(size) == dist_fact

mpi.finalize()
