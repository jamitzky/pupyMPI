#!/usr/bin/env python2.6

# Simple pupympi program to test sendrecv.
# This test is meant to be run with a odd number of processes

from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()


assert size % 2 == 1 # Require odd number of participants

content = "Chain Message"

DUMMY_TAG = 1

dest   = (rank + 1) % size
source = (rank + size-1) % size


print "SEND_RECV ==> ODD CHAIN SIZE TEST"
print "================================="
recvdata = mpi.MPI_COMM_WORLD.sendrecv(content, dest, DUMMY_TAG, source, DUMMY_TAG)
print "Rank %s received %s" % (rank, recvdata)

if rank < size-1:
    new_size = size-1

    dest   = (rank + 1) % new_size
    source = (rank + new_size-1) % new_size

    print "SEND_RECV ==> EVEN CHAIN SIZE TEST"
    print "================================="
    recvdata = mpi.MPI_COMM_WORLD.sendrecv(content, dest, DUMMY_TAG, source, DUMMY_TAG)
    print "Rank %s received %s" % (rank, recvdata)

print "All done %d of %d" % (rank, size)

# Close the sockets down nicely
mpi.finalize()
