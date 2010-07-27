#!/usr/bin/env python2.6
# meta-description: Test reduce, first compute factorial of mpi_size, then compare builtin ops max, min, sum to Python built-ins
# meta-expectedresult: 0
# meta-minprocesses: 10
# meta-max_runtime: 60

from mpi import MPI
from mpi.operations import MPI_prod,MPI_sum, MPI_avg, MPI_min, MPI_max

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

def b():
    mpi.MPI_COMM_WORLD.barrier()

dist_fact = mpi.MPI_COMM_WORLD.reduce(rank+1, MPI_prod, root=root)
dist_mpi_sum = mpi.MPI_COMM_WORLD.reduce(rank, MPI_sum, root=root)
dist_mpi_min = mpi.MPI_COMM_WORLD.reduce(rank, MPI_min, root=root)
dist_mpi_avg = mpi.MPI_COMM_WORLD.reduce(rank, MPI_avg, root=root)
dist_mpi_max = mpi.MPI_COMM_WORLD.reduce(rank, MPI_max, root=root)

dist_sum = mpi.MPI_COMM_WORLD.reduce(rank, sum, root=root)
dist_min = mpi.MPI_COMM_WORLD.reduce(rank, min, root=root)
dist_max = mpi.MPI_COMM_WORLD.reduce(rank, max, root=root)

if root == rank:
    print "-"*80
    print "Reducing with custom MPI operations"
    print "\tFactorial: %d" % dist_fact
    print "\tSum: %d" % dist_mpi_sum
    print "\tMin: %d" % dist_mpi_min
    print "\tMax: %d" % dist_mpi_max
    print "\tAvg: %d" % dist_mpi_avg
    print "\nReducing with built-in Python operations"
    print "\tSum: %d" % dist_sum
    print "\tMin: %d" % dist_min
    print "\tMax: %d" % dist_max
    print "-"*80

    assert fact(size) == dist_fact
    assert sum(range(size)) == dist_sum
    assert dist_sum == dist_mpi_sum
    assert dist_min == dist_mpi_min
    assert dist_max == dist_mpi_max
    assert dist_max == size-1
    assert dist_min == 0
    assert dist_mpi_avg == sum(range(size))/len(range(size))
else:
    assert dist_fact == None
    assert dist_sum == None
    assert dist_min == None
    assert dist_max == None
    assert dist_mpi_max == None
    assert dist_mpi_min == None
    assert dist_mpi_sum == None
    assert dist_mpi_avg == None

mpi.finalize()
