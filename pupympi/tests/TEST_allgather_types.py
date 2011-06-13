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


#### Test simple bytearray - everyone sends an array of chunksize elements
#chunksize = 5
#ba = bytearray(range(rank,rank+chunksize))
#received = world.allgather(ba)
#assert received == [bytearray(range(r,r+chunksize)) for r in range(size)]


### Test simple numpy array - everyone sends an array of chunksize elements
chunksize = 3
na = numpy.arange(rank,rank+chunksize)
received = world.allgather(na)
assert numpy.all( numpy.array(received) == numpy.array([numpy.arange(r,r+chunksize) for r in range(size)]) )


#### Test multidimensional numpy arrays - everyone sends an array of size*chunksize*2 elements
#chunksize = 4
#na = numpy.arange(rank*100,rank*100+size*chunksize*2).reshape(size*2,chunksize)
#received = world.allgather(na)
#
#control = numpy.array([numpy.arange(100*r,100*r+size*chunksize*2).reshape(size*2,chunksize) for r in range(size)]) 
#assert numpy.all( numpy.array(received) == control)


mpi.finalize()
