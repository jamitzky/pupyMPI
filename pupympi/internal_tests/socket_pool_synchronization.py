#!/usr/bin/env python2.6
"""
Test to provoke duplicate connections where processes try to send more or less simultaneously to each other resulting

Run with 4 procs and logging to show when _get_socket_for_rank returns a known socket in socketpool.add_accepted_socket
"""
from mpi import MPI
from mpi import constants


mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content = "Message from rank %d" % (rank)
DUMMY_TAG = 1


neighbours = range(size)

rRequests = []
sRequests = []

for n in neighbours:
    if rank == n: # skip self
        continue
    
    sRequest = mpi.MPI_COMM_WORLD.isend(content, n, DUMMY_TAG)
    rRequest = mpi.MPI_COMM_WORLD.irecv(n,DUMMY_TAG)    

    # store request objects
    rRequests.append(rRequest)
    sRequests.append(sRequest)

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

# Close the sockets down nicely
mpi.finalize()
