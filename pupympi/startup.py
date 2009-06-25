#!/usr/bin/env python2.6

import mpi

mpi = mpi.MPI()

import sys
print sys.argv

print "Started process %d of %d" % (mpi.rank(), mpi.size())

