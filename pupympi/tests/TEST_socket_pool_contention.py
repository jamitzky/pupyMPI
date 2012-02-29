#!/usr/bin/env python
# meta-description: Test when connections are attempted rapidly between many processes for a small socket pool
# meta-expectedresult: 0
# meta-minprocesses: 10
# meta-socket-pool-size: 5
# meta-max_runtime: 45

"""
NOTE: This test deviates from most other tests in that we have to peek into the
internal datastructures to check that the socket pool behaves as expected.

To ensure that the established socket connection between to processes is reused
we check the size of the socket pool directly.
"""

from mpi import MPI
from mpi import constants

import random

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content = "Message from rank %d" % (rank)
DUMMY_TAG = 1

f = open(constants.DEFAULT_LOGDIR+"mpi.socket_pool_contention.rank%s.log" % rank, "w")

neighbours = range(size)
random.seed(42) # Guaranteed random by fair dice roll (1d100)
random.shuffle(neighbours)

rRequests = []
sRequests = []

for n in neighbours:    

    f.write("Rank %d: posting isend and irecv to %d\n" % (rank,n) )
    f.flush()
    
    sRequest = mpi.MPI_COMM_WORLD.isend(content, n, DUMMY_TAG)
    rRequest = mpi.MPI_COMM_WORLD.irecv(n,DUMMY_TAG)    

    # store request objects
    rRequests.append(rRequest)
    sRequests.append(sRequest)
    
f.write("Rank %d: requests made\n" % (rank))
f.flush()

while rRequests or sRequests:
    
    
    (found, request) = mpi.MPI_COMM_WORLD.testany(rRequests)
    if found:
        # finish the request
        request.wait()
        rRequests.remove(request)
    
    (found, request) = mpi.MPI_COMM_WORLD.testany(sRequests)
    if found:
        # finish the request
        request.wait()
        sRequests.remove(request)

f.write("Rank %d: requests finished\n" % (rank))
f.flush()



# This test only makes sense for a dynamic socket pool
if mpi.network.socket_pool.readonly:
    f.write("Test skipped for rank %d since socket pool was static\n" % rank)
    f.flush()
else:
    f.write("Rank %d checking out the pool\n" % rank)
    f.write("\t %s \n" % mpi.network.socket_pool.sockets)
    f.flush()
    pool_size = len(mpi.network.socket_pool.sockets)
    # There should only be 5 connections as specified in meta-socket-pool-size (or 4???)
    if pool_size != 5:
        f.write("whoops pool size was not 5 but %i pool:\n" % (pool_size,mpi.network.socket_pool.metainfo) )
        f.flush()
    else:
        f.write("Done for rank %d\n" % rank)
        f.flush()
    
    assert pool_size == 5

f.close()

# Close the sockets down nicely
mpi.finalize()
