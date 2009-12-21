#!/usr/bin/env python2.6
# meta-description: allreduce, first computes factorial of mpi_size, then uses builtin max to find slowest process.
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI
from mpi.operations import prod,MPI_sum

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
# dist_sum = mpi.MPI_COMM_WORLD.reduce(rank+1, MPI_sum, root=root)
# print "Rank %s: dist_sum %s" % (rank, dist_sum)

if root == rank:
    assert fact(size) == dist_fact
    #assert sum(range(size)) == dist_sum
else:
    assert dist_fact == None
    assert dist_sum == None

mpi.finalize()
