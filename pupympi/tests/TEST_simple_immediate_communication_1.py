#!/usr/bin/env python2.6

# Simple pupympi program to test basic immediate communication

# first rank 0 isends timestamp to rank 1 who is a very slow reciever so rank 0 should quit early

import mpi, time

mpi = mpi.MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()


neighbour = (rank + 1) % size # Send to own rank + 1
content = "Message from rank %d" % (rank)

if rank == 0:
    # Send
    print "Rank: %d sending to %d" % (rank,neighbour)
    mpi.MPI_COMM_WORLD.isend(neighbour,content,"Dummy tag here")
    
    print "Rank: %d DONE" % (rank)
    
else: # rank == 1
    # Waaaaait for it...
    time.sleep(7)
    
    # Recieve
    print "Yawn, rank: %d recieving from %d" % (rank,neighbour)
    recieved = mpi.MPI_COMM_WORLD.irecv(neighbour,"Dummy tag here")    
    print "Rank: %d recieved %s" % (rank,recieved)

print "Sending/recieving done rank %d of %d after %d seconds sleep" % (rank, size, size-rank)

# Close the sockets down nicely
mpi.finalize()
