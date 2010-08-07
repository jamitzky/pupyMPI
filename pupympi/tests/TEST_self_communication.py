#!/usr/bin/env python2.6
# meta-description: Test communication with self
# meta-expectedresult: 0

# Simple pupympi program to test basically if it's possible to send to self.


from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD
rank = world.rank()
size = world.size()

DUMMY_TAG = 1
MESSAGE = "Test message with tag %d" % DUMMY_TAG

world.send( MESSAGE, rank, DUMMY_TAG)
msg = world.recv(rank, DUMMY_TAG)

assert msg == MESSAGE

# Close the sockets down nicely
mpi.finalize()
