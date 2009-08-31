#!/usr/bin/env python2.6

# Simple pupympi program to test basic blocking send to immediate recieve
# This test is meant to be run with only two processes

# rank 0 sends message1 and then message2 to rank 1 who first tries to recive
# message2 (based on tag) and then message1
# since message one was (blocking) sent first it should be the first message recieved

import time
from mpi import MPI

mpi = MPI.initialize()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()


neighbour = (rank + 1) % size # Communicate with own rank + 1
content1 = "This is message 1"
content2 = "This is message 2"

DUMMY_TAG = 1
ANOTHER_TAG = 2


if rank == 0:
    # Send
    print "Rank: %d sending to %d" % (rank,neighbour)
    request = mpi.MPI_COMM_WORLD.send(neighbour,content1,DUMMY_TAG)    
    request = mpi.MPI_COMM_WORLD.send(neighbour,content2,ANOTHER_TAG)    
    print "Rank: %d ALL DONE" % (rank)

    
else: # rank == 1
    
    # Recieve
    print "YAWN, rank: %d recieving from %d" % (rank,neighbour)
    request1 = mpi.MPI_COMM_WORLD.irecv(neighbour,ANOTHER_TAG)    
    recieved = request1.wait()
    print "Rank: %d RECIEVED %s for request1" % (rank,recieved)
    request2 = mpi.MPI_COMM_WORLD.irecv(neighbour,DUMMY_TAG)    
    recieved = request2.wait()
    print "Rank: %d RECIEVED %s for request2" % (rank,recieved)



print "Sending/recieving done rank %d of %d" % (rank, size)

# Close the sockets down nicely
mpi.finalize()
