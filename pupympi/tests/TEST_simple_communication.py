#!/usr/bin/env python2.6

# Simple pupympi program to test basic communication between to processes

import mpi, time
#from mpi import tcp


mpi = mpi.MPI()

rank = mpi.rank()
size = mpi.size()

time.sleep(max(2,size-rank))

# Send to own rank + 1
neighbour = (rank + 1) % size
content = "Message from rank %d" % (rank)
print "Rank: %d sending to %d" % (rank,neighbour)
mpi.isend(neighbour,content,"Dummy tag here")

print "Sending done rank %d of %d after %d seconds sleep" % (rank, size, size-rank)

# Close the sockets down nicely
mpi.finalize()
