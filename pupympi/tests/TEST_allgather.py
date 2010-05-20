#!/usr/bin/env python2.6
# meta-description: Test allgather, gathers rank from all processes and distributes to all
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

received = world.allgather(rank)

assert received == range(size)
    
mpi.finalize()