#!/usr/bin/env python2.6
# meta-description: allreduce, first computes factorial of mpi_size, then uses builtin max to find slowest process.
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI
from mpi.operations import prod

def fact(n):
    if n == 0:
        return 1
    else:
        return n * fact(n-1)
    
mpi = MPI()

root = 4

# We start n processes, and try to calculate n!
rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

dist_fact = mpi.MPI_COMM_WORLD.reduce(rank+1, prod, root=root)

if root == rank:
    assert fact(size) == dist_fact
else:
    assert dist_fact == None

mpi.finalize()
