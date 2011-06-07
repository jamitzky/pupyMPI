#!/usr/bin/env python2.6
# meta-description: Gather test, receive information from all processes to one
# meta-expectedresult: 0
# meta-minprocesses: 10
import numpy

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

# Every processes sends rank to the root
ROOT = 2

# Test numpy arrays everyone sends an array of three elements
na = numpy.arange(rank,rank+3)
received = world.gather(na, root=ROOT)
if ROOT == rank:
    #assert received == [numpy.arange(r,r+3) for r in range(size)]
    print "Rank:%i received:%s" % (rank, received)
else:
    #assert received == None
    pass


mpi.finalize()
