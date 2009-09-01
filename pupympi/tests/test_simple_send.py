#!/usr/bin/env python2.6

# Simple pupympi program to test basic immediate send to immediate recieve
# This test is meant to be run with only two processes

# first rank 0 isends message to rank 1 

import time
from mpi import MPI

mpi = MPI.initialize()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()


neighbour = (rank + 1) % size # Communicate with own rank + 1
content = "This message was what I sent (isend)"

DUMMY_TAG = 1


if rank == 0:
    # Send
    print "Rank: %d sending to %d" % (rank,neighbour)
    request = mpi.MPI_COMM_WORLD.isend(neighbour,content,DUMMY_TAG)
    print "Rank: %d DONE sending to %d" % (rank,neighbour)
    request.wait()
    
    print "Rank: %d ALL DONE" % (rank)

    
else: # rank == 1
    
    # Recieve
    print "YAWN, rank: %d recieving from %d" % (rank,neighbour)
    request = mpi.MPI_COMM_WORLD.irecv(neighbour,DUMMY_TAG)    
    recieved = request.wait()
    print "Rank: %d RECIEVED %s" % (rank,recieved)


print "Sending/recieving done rank %d of %d" % (rank, size)

# Close the sockets down nicely
mpi.finalize()
