#!/usr/bin/env python2.6
# meta-description: Gather test, receive information from all processes to one
# meta-expectedresult: 0
# meta-minprocesses: 10
import numpy

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

# Every processes sends rank to the root
ROOT = 3
received = world.gather(rank, root=ROOT)
if ROOT == rank:
    assert received == range(0, size)
else:
    assert received == None

# Test list, make every processes sends rank range to the root
ROOT = 2
received = world.gather(range(rank), root=ROOT)
if ROOT == rank:
    assert received == [range(r) for r in range(size)]
    print received
else:
    assert received == None

mpi.finalize()
