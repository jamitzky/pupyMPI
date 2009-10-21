#!/usr/bin/env python2.6
# meta-description: Test if mpi_bcast work. 
# meta-expectedresult: 0
# meta-minprocesses: 11

from mpi import MPI
BCAST_MESSAGE = "Test message"
mpi = MPI()
size = mpi.MPI_COMM_WORLD.size()
assert size > 2

if mpi.MPI_COMM_WORLD.rank() == 3:
    mpi.MPI_COMM_WORLD.bcast(3, BCAST_MESSAGE)
else:
    message = mpi.MPI_COMM_WORLD.bcast(3)
    print message
    assert message == BCAST_MESSAGE

mpi.finalize()
