#!/usr/bin/env python
# meta-description: Test abort, rank 0 will abort right away, other processes will sleep and should not exit with code 0
# meta-expectedresult: 1
# meta-minprocesses: 4

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

if world.rank() == 0:
    mpi.abort()
else:
    import time, sys
    time.sleep(4)

    #print "We're about to sys exit with a positive return value"

    # If we get to this line the abort stuff has not worked
    # so we actually return nicely, which is not expected.
    sys.exit(0)
