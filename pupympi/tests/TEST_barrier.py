#!/usr/bin/env python2.6
# meta-description: Test if barriers work and do so tightly
# meta-expectedresult: 0
# meta-minprocesses: 11

# Simple pupympi program to test barrier
# All ranks synchronize at barrier
# Rank 0 sleeps for 5 seconds before joining the next barrier
# all ranks should see at least a 5 second interval between t1 and t2 caused
# by waiting for rank 0 at the second barrier
# NOTE: The interval could be slightly less as discussed in issue 65
# http://bitbucket.org/bromer/python-mpi/issue/65/
# For this reason we currently allow a 0.05 variance

from mpi import MPI

import time
from datetime import datetime

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

#print "%s: I am the process with rank %d of %d processes, now barrier'ing" % (datetime.now(), rank, size)
mpi.MPI_COMM_WORLD.barrier()

t1 = time.time()

if rank == 0:
    time.sleep(5)

mpi.MPI_COMM_WORLD.barrier()

t2 = time.time()

assert ((t2 - t1) > 4.95), " Rank %i failed with (t2 - t1) = %s " % (rank, (t2-t1))

#if not (t2 - t1) > 5.0:
#    print "Rank %i failed with (t2 - t1) = %s " % (rank, (t2-t1))
#else:
#    print "Ok for rank %i with (t2 - t1) = %s " % (rank, (t2-t1))
#print "%s: I am the process with rank %d of %d processes, past barrier" % (datetime.now(), rank, size)

# Close the sockets down nicely
mpi.finalize()
