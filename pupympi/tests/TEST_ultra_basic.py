#!/usr/bin/env python2.6

# Simplest pupympi program to test startup of one process doing nothing but printing

from sys import stderr
from mpi import MPI

mpi = MPI()


print "There can be only one."

# Close the sockets down nicely
mpi.finalize()
