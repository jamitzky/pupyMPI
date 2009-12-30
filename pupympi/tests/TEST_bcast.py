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
BCAST_FIRST_MESSAGE = "Test message for rank %d" % BCAST_ROOT

messages = [BCAST_FIRST_MESSAGE, None, "", -1]

for msg in messages:
    if rank == BCAST_ROOT:
        world.bcast(BCAST_ROOT, msg)
    else:
        message = world.bcast(BCAST_ROOT)
        print "-"*80
        print msg
        print message
        print "-"*80
        assert message == msg 

mpi.finalize()
