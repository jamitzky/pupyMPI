#!/usr/bin/env python2.6
# meta-description: gather, Receives information from all processes to one. 
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

# Make every processes send their rank to the root. 

ROOT = 3

received = world.gather(rank, root=ROOT)

if ROOT == rank:
    assert received == range(0, size)
else:
    assert received == None
    
mpi.finalize()
