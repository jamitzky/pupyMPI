#!/usr/bin/env python2.6
# meta-description: Test if mpi_bcast work. 
# meta-expectedresult: 0
# meta-minprocesses: 11

import random
from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

BCAST_ROOT = 3
BCAST_MESSAGE = "Test message for rank %d" % BCAST_ROOT

if rank == BCAST_ROOT:
    mpi.MPI_COMM_WORLD.bcast(BCAST_ROOT, BCAST_MESSAGE)
else:
    message = mpi.MPI_COMM_WORLD.bcast(BCAST_ROOT)
    print message
    assert message == BCAST_MESSAGE

mpi.finalize()
