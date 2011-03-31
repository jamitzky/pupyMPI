#!/usr/bin/env python2.6
# meta-description: Test allgather, gathers rank from all processes and distributes to all
# meta-expectedresult: 0
# meta-minprocesses: 10
# meta-max_runtime: 25

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

#received = world.allgather(rank)
#
#assert received == range(size)

# ensure we can work with sequences
gather_data = [rank for _ in range(10)]

my_data = world.allgather(gather_data)
#DEBUG
#print "rank %i done gathering" % rank
expected_data = [ [r for _ in range(10)] for r in range(size) ]

assert my_data == expected_data
mpi.finalize()
