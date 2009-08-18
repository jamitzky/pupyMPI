#!/usr/bin/env python2.6

# Is this test program used anymore???

# Simple pupympi program to test basic communication between to processes

import time
from mpi import tcp, MPI

MY_TAG = 12

mpi = MPI.initialize()

rank = mpi.rank()
size = mpi.size()

if rank == 0:
    mpi.send(1, "My contents", MY_TAG)
else:
    data = mpi.recv(1, MY_TAG)
    print "Got data: ", data

# Close the sockets down nicely
mpi.finalize()
