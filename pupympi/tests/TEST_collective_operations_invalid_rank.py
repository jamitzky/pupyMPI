#!/usr/bin/env python2.6
# meta-description: Test all the collective operations receiving a root parameter what happens with an invalid root
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI
from mpi.exceptions import MPINoSuchRankException

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

# Make every processes send their rank to the root. 
try:
    world.gather(rank, root=size)
except Exception, e:
    assert type(e) == MPINoSuchRankException

try:
    world.reduce(rank, sum, size)
except Exception, e:
    assert type(e) == MPINoSuchRankException
   
try:
    world.bcast(size, rank)
except Exception, e:
    assert type(e) == MPINoSuchRankException

try:
    world.scatter(range(size), root=size)
except Exception, e:
    assert type(e) == MPINoSuchRankException

mpi.finalize()
