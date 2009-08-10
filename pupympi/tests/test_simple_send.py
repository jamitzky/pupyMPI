#!/usr/bin/env python2.6

# Simple pupympi program to test basic communication between to processes

import mpi, time
from mpi import tcp

MY_TAG = 12

mpi = mpi.MPI()

rank = mpi.rank()
size = mpi.size()

if rank == 0:
    mpi.send(1, "My contents", MY_TAG)
else:
    data = mpi.recv(1, MY_TAG)
    print "Got data: ", data

# Close the sockets down nicely
mpi.finalize()
