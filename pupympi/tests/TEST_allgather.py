#!/usr/bin/env python2.6
# meta-description: allgather, gathers information from all the processes and distributes them to all.
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

received = world.allgather(rank+1)

assert received == range(1,size+1)
    
mpi.finalize()