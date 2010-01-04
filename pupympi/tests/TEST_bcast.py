#!/usr/bin/env python2.6
# meta-description: Test if broadcast works
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
        world.bcast(msg, BCAST_ROOT)
    else:
        message = world.bcast(root=BCAST_ROOT)
        try:
            assert message == msg 
        except AssertionError, e:
            print "="*80
            print "Expected", msg
            print "Received", message
            print "="*80
            raise e

mpi.finalize()
