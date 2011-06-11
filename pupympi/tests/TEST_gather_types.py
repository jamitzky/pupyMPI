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

ROOT = 2
#ROOT = 0

### gather an int
#received = world.gather(rank, root=ROOT)
#if ROOT == rank:
#    assert received == range(size)
#else:
#    assert received == None
#
### gather a string
#received = world.gather("im the real rank:%i"%rank, root=ROOT)
#if ROOT == rank:
#    assert received == [ "im the real rank:%i"%r for r in range(size) ]
#else:
#    assert received == None
#

## gather a bytearray
received = world.gather(bytearray("im the real rank:%i"%rank), root=ROOT)
if ROOT == rank:
    assert received == [bytearray("im the real rank:%i"%r) for r in range(size) ]
else:
    assert received == None


## Test numpy arrays everyone sends an array of chunksize elements
#chunksize = 3
#na = numpy.arange(rank,rank+chunksize)
#received = world.gather(na, root=ROOT)
#if ROOT == rank:
#    assert numpy.all( numpy.array(received) == numpy.array([numpy.arange(r,r+chunksize) for r in range(size)]) )
#    #received = [numpy.arange(r,r+chunksize) for r in range(size)]
#    print "Rank:%i received:%s" % (rank, received)
#else:
#    #assert received == None
#    pass


mpi.finalize()
