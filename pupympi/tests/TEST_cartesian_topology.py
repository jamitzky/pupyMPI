#!/usr/bin/env python2.6
# meta-description: Baseline test of cartesian topologies (use CartesianTest class to be thorough)
# meta-expectedresult: 0
# meta-minprocesses: 8

from mpi import MPI
from mpi.topology.Cartesian import Cartesian

mpi = MPI()
rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

cart = Cartesian(mpi.MPI_COMM_WORLD, [2,2,2], [True, True, True])
assert cart is not None
if rank == 4:
    assert cart.get() == [0,0,1]
assert cart.coords(4) == [0,0,1]
assert cart.rank([0,0,0]) == 0 # first process
assert cart.rank([1,1,1]) == size-1 # last process

mpi.finalize()
