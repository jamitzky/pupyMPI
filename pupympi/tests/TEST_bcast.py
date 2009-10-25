#!/usr/bin/env python2.6
# meta-description: Test if mpi_bcast work. 
# meta-expectedresult: 0
# meta-minprocesses: 11

import time
start_time = time.time()

from mpi import MPI
BCAST_MESSAGE = "Test message"
mpi = MPI()
init_time = time.time()

BCAST_ROOT = 0

print "Init time: %f" % (init_time-start_time)

size = mpi.MPI_COMM_WORLD.size()
assert size > 2

if mpi.MPI_COMM_WORLD.rank() == BCAST_ROOT:
    mpi.MPI_COMM_WORLD.bcast(BCAST_ROOT, BCAST_MESSAGE)
else:
    message = mpi.MPI_COMM_WORLD.bcast(BCAST_ROOT)
    print message
    assert message == BCAST_MESSAGE

logic_time = time.time()

mpi.finalize()

finalize_time = time.time()

print """
TIME INFORMATION
    Initialization: %f 
    Logic: %f
    Finalization: %f
    Total: %f """ % (init_time - start_time, logic_time - init_time, finalize_time - logic_time, finalize_time - start_time) 
