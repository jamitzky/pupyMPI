#!/usr/bin/env python2.6
# meta-description: Simple pupympi program to test basic immediate send to blocking receive
# meta-expectedresult: 0
# meta-minprocesses: 2

# rank 0 isends message to rank 1 who is a very slow receiver so rank 0 should quit early

import time

from mpi import MPI
import time

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content = "This message was Isent"

DUMMY_TAG = 1

if rank == 0:
    # Send
    neighbour = 1
    print "Rank: %d sending to %d" % (rank,neighbour)
    request = mpi.MPI_COMM_WORLD.isend(content, neighbour, DUMMY_TAG)
    print "Rank: %d DONE sending to %d" % (rank,neighbour)
    request.wait()
    
    #print "Rank: %d ALL DONE" % (rank)
elif rank == 1: 
    # Waaaaait for it...
    time.sleep(3)
    
    neighbour = 0
    
    # Receive
    print "YAWN, rank: %d receiving from %d" % (rank,neighbour)
    received = mpi.MPI_COMM_WORLD.recv(neighbour,DUMMY_TAG)    
    print "Rank: %d RECEIVED %s" % (rank,received)
    time.sleep(1)

else:
    #print "I'm rank %d and I'm not doing anything in this test" % rank
    pass

print "Sending/receiving done rank %d of %d" % (rank, size)

# Close the sockets down nicely
mpi.finalize()
