#!/usr/bin/env python
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
assert recvdata == content+" from "+str(source)

# Testing up/down synchronization
lower = dest # lower neighbour has rank+1
upper = source # upper neighbour has rank-1

if rank != 0:
    # exchange up
    recvdata = mpi.MPI_COMM_WORLD.sendrecv("border of "+str(rank), upper, DUMMY_TAG, upper, DUMMY_TAG)
    assert recvdata == "border of "+str(upper)
    #print "r:%i UP recvdata:%s" % (rank,recvdata)
if rank != size-1:
    # exchange down
    recvdata = mpi.MPI_COMM_WORLD.sendrecv("border of "+str(rank), lower, DUMMY_TAG, lower, DUMMY_TAG)
    assert recvdata == "border of "+str(lower)
    #print "r:%i DOWN recvdata:%s" % (rank,recvdata)

# Testing with shorthand
if rank != 0:
    # exchange up
    recvdata = mpi.MPI_COMM_WORLD.sendrecv("2nd border of "+str(rank), upper)
    assert recvdata == "2nd border of "+str(upper)
    #print "r:%i UP recvdata:%s" % (rank,recvdata)
if rank != size-1:
    # exchange down
    recvdata = mpi.MPI_COMM_WORLD.sendrecv("2nd border of "+str(rank), lower)
    assert recvdata == "2nd border of "+str(lower)
    #print "r:%i DOWN recvdata:%s" % (rank,recvdata)


# Close the sockets down nicely
mpi.finalize()
