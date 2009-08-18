#!/usr/bin/env python2.6

from mpi import MPI

mpi = MPI.initialize()

import sys
print sys.argv

mpi.finalize()
