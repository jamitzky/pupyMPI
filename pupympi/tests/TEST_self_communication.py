#!/usr/bin/env python2.6

# Simple pupympi program to test basic if it's possible
# to send to self.

# rank 0 sends message to rank 1 
from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD
rank = world.rank()
size = world.size()

DUMMY_TAG = 1
MESSAGE = "Test message with tag %d" % DUMMY_TAG

world.send(rank, MESSAGE, DUMMY_TAG)
msg = world.recv(rank, DUMMY_TAG)

assert msg == MESSAGE

# Close the sockets down nicely
mpi.finalize()
