#!/usr/bin/env python2.6
# meta-description: test basic immediate communication. First rank 0 isends timestamp to rank 1 who is a very slow reciever so rank 0 should quit early
# meta-expectedresult: 0
# meta-minprocesses: 2

import time
from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content = "Message from rank %d" % (rank)
DUMMY_TAG = 1

if rank == 0:
    neighbour = 1
    # Send
    print "Rank: %d sending to %d" % (rank,neighbour)
    request = mpi.MPI_COMM_WORLD.isend(neighbour,content,DUMMY_TAG)
    request.wait()
    
    print "Rank: %d DONE" % (rank)

    
elif rank == 1: 
    neighbour = 0
    
    # Recieve
    print "Yawn, rank: %d recieving from %d" % (rank,neighbour)
    request = mpi.MPI_COMM_WORLD.irecv(neighbour,DUMMY_TAG)    
    recieved = request.wait()
    print "Rank: %d recieved %s" % (rank,recieved)
else:
    print "I'm rank %d and I'm not doing anything in this test" % rank

print "Sending/recieving done rank %d of %d after %d seconds sleep" % (rank, size, size-rank)

# Close the sockets down nicely
mpi.finalize()
