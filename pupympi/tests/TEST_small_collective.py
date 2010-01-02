#!/usr/bin/env python2.6
# meta-description: Test if it's possible to create a really small collective operation. 
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

# Make every processes send their rank to the root. 

ROOT = 0

received = world.gather(rank, root=0)

if ROOT == rank:
    assert received == range(0, size)
else:
    assert received == None
    
mpi.finalize()
