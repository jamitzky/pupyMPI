#!/usr/bin/env python2.6
# meta-description: Test if mpi_bcast work. 
# meta-expectedresult: 0
# meta-minprocesses: 11

import random
from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

BCAST_ROOT = 3
BCAST_MESSAGE = "Test message for rank %d" % BCAST_ROOT

if rank == BCAST_ROOT:
    world.bcast(BCAST_ROOT, BCAST_MESSAGE)
else:
    message = world.bcast(BCAST_ROOT)
    try:
        assert message == BCAST_MESSAGE
    except AssertionError, e:
        print "Excepted data:", BCAST_MESSAGE
        print "Received data:", message
        raise e
mpi.finalize()
