#!/usr/bin/env python2.6
# meta-description: Test if broadcast works with all types
# meta-expectedresult: 0
# meta-minprocesses: 11
import numpy

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

BCAST_ROOT = 2

l = range(100)
d = dict( [ (str(i),i) for i in l] )
t = tuple(l)
na = numpy.array(l)
naf = numpy.array([ i/3.0 for i in l] )
ba = bytearray("abcdefg")

messages = [l,d,t,na,naf]

for msg in messages:
    if rank == BCAST_ROOT:
        world.bcast(msg, BCAST_ROOT)
    else:
        message = world.bcast(root=BCAST_ROOT)
        try:
            numpy.alltrue(message == msg)
        except AssertionError, e:
            print "="*80
            print "Expected", msg
            print "Received", message
            print "="*80
            raise e

mpi.finalize()
