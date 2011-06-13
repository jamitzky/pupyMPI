#!/usr/bin/env python2.6
# meta-description: Test allgather, gathers rank from all processes and distributes to all
# meta-expectedresult: 0
# meta-minprocesses: 10
# meta-max_runtime: 25
import numpy

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

### Test simple numpy array - everyone sends an array of chunksize elements
chunksize = 3
na = numpy.arange(rank,rank+chunksize)
received = world.allgather(na)
if rank == 0:
    print "rank:% received:%s" % (rank, received)
    assert numpy.all( numpy.array(received) == numpy.array([numpy.arange(r,r+chunksize) for r in range(size)]) )
else:
    assert received == None

mpi.finalize()
