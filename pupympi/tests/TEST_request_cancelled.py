#!/usr/bin/env python2.6
# meta-description: allreduce, first computes factorial of mpi_size, then uses builtin max to find slowest process.
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD
TAG = 1

if world.rank() == 1:
    req1 = world.isend(0, "My message 1", TAG)

    assert not req1.test_cancelled()
    
    req1.cancel()
    
    assert req1.test_cancelled()
else:
    req1 = world.irecv(1, TAG)

    assert not req1.test_cancelled()
    
    req1.cancel()
    
    assert req1.test_cancelled()

mpi.finalize()