#!/usr/bin/env python2.6

# Simple pupympi program to test basic blocking communication between two processes
# only works for two processes

# first rank 0 sends then 1 recieves, then vice versa

import time
from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

if size < 2:
    print "WHAT ARE YOU DOING?"


content = "HELLO.. This is my bloddy message from rank %d" % (rank)

DUMMY_TAG = 1

if rank == 0:
    # Send
    neighbour = 1
    print "Rank: %d sending to %d" % (rank,neighbour)
    mpi.MPI_COMM_WORLD.send(neighbour,content, DUMMY_TAG)

    # Recieve
    print "Rank: %d recieving from %d" % (rank,neighbour)
    recieved = mpi.MPI_COMM_WORLD.recv(neighbour, DUMMY_TAG)    
    print "Rank: %d recieved '%s'" % (rank,recieved)

elif rank == 1:
    # Recieve
    neighbour = 0
    print "Rank: %d recieving from %d" % (rank,neighbour)
    recieved = mpi.MPI_COMM_WORLD.recv(neighbour, DUMMY_TAG)    
    print "Rank: %d recieved '%s'" % (rank,recieved)
    
    # Send
    print "Rank: %d sending to %d" % (rank,neighbour)
    mpi.MPI_COMM_WORLD.send(neighbour,content, DUMMY_TAG)
else: # rank == 1
    print "Im doing nothing"

print "Sending/recieving done rank %d of %d after %d seconds sleep" % (rank, size, size-rank)

# Close the sockets down nicely
mpi.finalize()
