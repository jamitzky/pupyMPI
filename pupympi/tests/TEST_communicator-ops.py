#!/usr/bin/env python2.6

# Simple pupympi program to test all communicator ops

from mpi import MPI
from sys import stderr

mpi = MPI()

newgroup = mpi.MPI_COMM_WORLD.group()

newcomm_full = mpi.MPI_COMM_WORLD.comm_create(newgroup)
assert newcomm_full is not None

# Close the sockets down nicely
mpi.finalize()
