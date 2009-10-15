#!/usr/bin/env python2.6
# meta-description: tests if crashes in MPI program are propagated back to initiator
# meta-expectedresult: 1

# Simple pupympi program to test if horribly broken scripts manage to return their stderr

from mpi import MPI
from sys import stderr
from threading import Thread, Condition, activeCount, currentThread 

#print "Threads before initialize %s" % activeCount()
mpi = MPI()
#print "Threads after initialize %s" % activeCount()

raise Exception("Forced error from rank %s" % mpi.MPI_COMM_WORLD.rank())

# Close the sockets down nicely
mpi.finalize()
