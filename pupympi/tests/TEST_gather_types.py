#!/usr/bin/env python
# meta-description: Gather testing of different types
# meta-expectedresult: 0
# meta-minprocesses: 10
import numpy

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

ROOT = 3

### gather an int
received = world.gather(rank, root=ROOT)
if ROOT == rank:
    assert received == range(size)
else:
    assert received == None


### gather a string
received = world.gather("im the real rank:%i"%rank, root=ROOT)
if ROOT == rank:
    assert received == [ "im the real rank:%i"%r for r in range(size) ]
else:
    assert received == None


### gather a bytearray
received = world.gather(bytearray("im the real rank:%i"%rank), root=ROOT)
if ROOT == rank:
    assert received == [bytearray("im the real rank:%i"%r) for r in range(size) ]
else:
    assert received == None


### Test simple numpy array - everyone sends an array of chunksize elements
chunksize = 3
na = numpy.arange(rank,rank+chunksize)
received = world.gather(na, root=ROOT)
if ROOT == rank:
    assert numpy.all( numpy.array(received) == numpy.array([numpy.arange(r,r+chunksize) for r in range(size)]) )
else:
    assert received == None


### Test multidimensional numpy arrays - everyone sends an array of size*chunksize*2 elements
chunksize = 3
na = numpy.arange(rank*100,rank*100+size*chunksize*2).reshape(size*2,chunksize)
received = world.gather(na, root=ROOT)

if ROOT == rank:
    control = numpy.array([numpy.arange(100*r,100*r+size*chunksize*2).reshape(size*2,chunksize) for r in range(size)]) 
    assert numpy.all( numpy.array(received) == control)
else:
    assert received == None

mpi.finalize()
