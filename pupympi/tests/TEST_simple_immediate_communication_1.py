#!/usr/bin/env python2.6

# Simple pupympi program to test basic immediate communication

# first rank 0 isends timestamp to rank 1 who is a very slow reciever so rank 0 should quit early

import time
from mpi import MPI

mpi = MPI.initialize()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()


neighbour = (rank + 1) % size # Send to own rank + 1
content = "Message from rank %d" % (rank)

if rank == 0:
    # Send
    print "Rank: %d sending to %d" % (rank,neighbour)
    request = mpi.MPI_COMM_WORLD.isend(neighbour,content,"Dummy tag here")
    request.wait()
    
    print "Rank: %d DONE" % (rank)

    
else: # rank == 1
    # TOFIX: This sleep actually deadlocks the program - it shouldn't
    # Waaaaait for it...
    time.sleep(4)
    
    # Recieve
    print "Yawn, rank: %d recieving from %d" % (rank,neighbour)
    request = mpi.MPI_COMM_WORLD.irecv(neighbour,"Dummy tag here")    
    recieved = request.wait()
    print "Rank: %d recieved %s" % (rank,recieved)


print "Sending/recieving done rank %d of %d after %d seconds sleep" % (rank, size, size-rank)

# Close the sockets down nicely
mpi.finalize()
