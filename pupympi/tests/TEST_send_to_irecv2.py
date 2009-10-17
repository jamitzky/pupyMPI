#!/usr/bin/env python2.6

# Simple pupympi program to test basic blocking send to immediate recieve
# This test is meant to be run with only two processes

# Rank 0 sends message2 and then message1 to rank 1 who first tries to recive
# message1 (based on tag) and then message2
# That is message1 should be recieved first then message2

import time
from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content1 = "This is message 1"
content2 = "This is message 2"

DUMMY_TAG = 1
ANOTHER_TAG = 2

if rank == 0:
    neighbour = 1
    # Send
    print "Rank: %d sending to %d" % (rank,neighbour)
    request = mpi.MPI_COMM_WORLD.send(neighbour,content2,DUMMY_TAG)    
    request = mpi.MPI_COMM_WORLD.send(neighbour,content1,ANOTHER_TAG)    
    print "Rank: %d ALL DONE" % (rank)

elif rank == 1:
    neighbour = 0
    # Recieve
    print "YAWN, rank: %d recieving from %d" % (rank,neighbour)
    request1 = mpi.MPI_COMM_WORLD.irecv(neighbour,ANOTHER_TAG)    
    recieved = request1.wait()
    print "Rank: %d RECIEVED %s for request1" % (rank,recieved)
    request2 = mpi.MPI_COMM_WORLD.irecv(neighbour,DUMMY_TAG)    
    recieved = request2.wait()
    print "Rank: %d RECIEVED %s for request2" % (rank,recieved)
else: 
    print "I'm rank %d and I'm not doing anything in this test" % rank



print "Sending/recieving done rank %d of %d" % (rank, size)

# Close the sockets down nicely
mpi.finalize()
