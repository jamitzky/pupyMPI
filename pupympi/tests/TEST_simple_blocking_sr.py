#!/usr/bin/env python2.6
# meta-description: test basic blocking communication. first rank 0 sends then 1 recieves, then vice versa.
# meta-expectedresult: 0
# meta-minprocesses: 2

import time
from mpi import MPI
from mpi import constants

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

assert size > 1

def get_content(rank):
    return "HELLO.. This is my bloddy message from rank %d" % (rank)

DUMMY_TAG = 1

if rank == 0:
    # Send
    neighbour = 1
    #print "Rank: %d sending to %d" % (rank,neighbour)
    mpi.MPI_COMM_WORLD.send(neighbour, get_content(rank), DUMMY_TAG)

    # Recieve
    #print "Rank: %d recieving from %d" % (rank,neighbour)
    recieved = mpi.MPI_COMM_WORLD.recv(neighbour, DUMMY_TAG)    
    
    assert recieved==get_content(neighbour)
    #print "Rank: %d recieved '%s'" % (rank,recieved)

elif rank == 1:
    # Recieve
    neighbour = 0
    #print "Rank: %d recieving from %d" % (rank,neighbour)
    recieved = mpi.MPI_COMM_WORLD.recv(neighbour, DUMMY_TAG)    
    #print "Rank: %d recieved '%s'" % (rank,recieved)
    
    assert recieved==get_content(neighbour)
    
    # Send
    #print "Rank: %d sending to %d" % (rank,neighbour)
    mpi.MPI_COMM_WORLD.send(neighbour, get_content(rank), DUMMY_TAG)
    
else: # rank == 1
    #print "Im doing nothing"
    pass

#print "Sending/recieving done rank %d of %d after %d seconds sleep" % (rank, size, size-rank)

# Close the sockets down nicely
mpi.finalize()
