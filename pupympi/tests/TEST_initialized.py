#!/usr/bin/env python2.6

import time
from mpi import MPI

assert not MPI.initialized(), "The mpi environment was initialized before starting mpi.. wrong"

mpi = MPI()

assert MPI.initialized(), "The mpi environment was not initialized after starting mpi.. wrong"

# Close the sockets down nicely
mpi.finalize()

