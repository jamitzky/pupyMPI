#!/usr/bin/env python2.6
# meta-description: Test basic blocking communication. First rank 0 sends then 1 receives, then vice versa.
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

assert size > 1

def get_content(rank):
    return "HELLO.. This is a message from rank %d" % (rank)

DUMMY_TAG = 1

if rank == 0:
    # Send
    neighbour = 1
    #print "Rank: %d sending to %d" % (rank,neighbour)
    mpi.MPI_COMM_WORLD.send(get_content(rank), neighbour, DUMMY_TAG)

    # Receive
    #print "Rank: %d receiving from %d" % (rank,neighbour)
    received = mpi.MPI_COMM_WORLD.recv(neighbour, DUMMY_TAG)    
    
    assert received==get_content(neighbour)
    #print "Rank: %d received '%s'" % (rank,received)

elif rank == 1:
    # Receive
    neighbour = 0
    #print "Rank: %d receiving from %d" % (rank,neighbour)
    received = mpi.MPI_COMM_WORLD.recv(neighbour, DUMMY_TAG)    
    #print "Rank: %d received '%s'" % (rank,received)
    
    assert received==get_content(neighbour)
    
    # Send
    #print "Rank: %d sending to %d" % (rank,neighbour)
    mpi.MPI_COMM_WORLD.send(get_content(rank), neighbour, DUMMY_TAG)
    
else: # rank == 1
    #print "Im doing nothing"
    pass

#print "Sending/receiving done rank %d of %d after %d seconds sleep" % (rank, size, size-rank)

# Close the sockets down nicely
mpi.finalize()
