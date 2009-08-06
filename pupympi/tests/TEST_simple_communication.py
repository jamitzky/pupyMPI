#!/usr/bin/env python2.6

# Simple pupympi program to test basic communication between two processes

import mpi, time
#from mpi import tcp


mpi = mpi.MPI()

rank = mpi.rank()
size = mpi.size()

time.sleep(max(2,size-rank)) # NOTE: Why sleep here?

# 0 sends to 1
neighbour = (rank + 1) % size # Send to own rank + 1

if rank == 0:
    content = "Message from rank %d" % (rank)
    print "Rank: %d sending to %d" % (rank,neighbour)
    mpi.isend(neighbour,content,"Dummy tag here")
else: # rank == 1
    print "Rank: %d recieving from %d" % (rank,neighbour)
    recieved = mpi.irecv(neighbour,"Dummy tag here")    
    print "Rank: %d recieved %s" % (rank,recieved)

print "Sending/recieving done rank %d of %d after %d seconds sleep" % (rank, size, size-rank)

# Close the sockets down nicely
mpi.finalize()
