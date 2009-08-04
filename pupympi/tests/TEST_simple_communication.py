#!/usr/bin/env python2.6

# Simple pupympi program to test basic communication between to processes

import mpi, time
from mpi import tcp

mpi = mpi.MPI()

rank = mpi.rank()
size = mpi.size()

SOME_TAG = 13

if rank == 0:
    mpi.send(1, "My message to the other side", SOME_TAG)
else:
    msg = mpi.recv(0, SOME_TAG)
    print "Got message", msg

# Close the sockets down nicely
mpi.finalize()
