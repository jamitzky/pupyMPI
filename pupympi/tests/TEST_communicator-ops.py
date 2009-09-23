#!/usr/bin/env python2.6

# Simple pupympi program to test all communicator ops

from mpi import MPI
from sys import stderr

mpi = MPI()

newgroup = mpi.MPI_COMM_WORLD.group()

newcomm_full = mpi.MPI_COMM_WORLD.comm_create(newgroup)
assert newcomm_full is not None
print "Communicator ID: %s" % newcomm_full.id

newcomm_full2 = mpi.MPI_COMM_WORLD.comm_create(newgroup)
assert newcomm_full2 is not None
print "Communicator ID: %s" % newcomm_full2.id

newcomm_full3 = newcomm_full.comm_create(newgroup)
assert newcomm_full3 is not None
print "Communicator ID: %s" % newcomm_full3.id

newcomm_full4 = newcomm_full2.comm_create(newgroup)
assert newcomm_full4 is not None
print "Communicator ID: %s" % newcomm_full4.id


# Close the sockets down nicely
mpi.finalize()
