#!/usr/bin/env python2.6
# meta-description: Testing the sendrecv call. All processes pass a token around
# meta-expectedresult: 0
# meta-minprocesses: 5
# meta-max_runtime: 90


from mpi import MPI
from mpi import constants

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content = "conch"
DUMMY_TAG = 1

# Send up in chain, recv from lower (with usual wrap around)
dest   = (rank + 1) % size
source = (rank - 1) % size

recvdata = mpi.MPI_COMM_WORLD.sendrecv(content+" from "+str(rank), dest, DUMMY_TAG, source, DUMMY_TAG)
print "r:%i recvdata:%s" % (rank,recvdata)

# Testing up/down partitioning
lower = dest # lower neighbour has rank+1
upper = source # upper neighbour has rank-1

if rank != 0:
    # Send up
    recvdata = mpi.MPI_COMM_WORLD.sendrecv("border of "+str(rank), upper, DUMMY_TAG, upper, DUMMY_TAG)
    print "r:%i UP recvdata:%s" % (rank,recvdata)
if rank != size-1:
    # Send down
    recvdata = mpi.MPI_COMM_WORLD.sendrecv("border of "+str(rank), lower, DUMMY_TAG, lower, DUMMY_TAG)
    print "r:%i DOWN recvdata:%s" % (rank,recvdata)

# Close the sockets down nicely
mpi.finalize()
