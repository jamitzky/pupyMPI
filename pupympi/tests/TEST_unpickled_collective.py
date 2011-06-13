#!/usr/bin/env python2.6
# meta-description: Test sending without serialization
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-max_runtime: 25

"""
ISSUE: This test is to be used with debug output that shows the unpickled control
        path being taken.
        As a part of runtest it only goes to show that various dimensions of arrays
        can be sent.
        Consider folding the interesting array-sending into an existing numpy test
        or try to find a hook into the raw data queue
"""

import numpy

from mpi import MPI
from mpi.collective.operations import MPI_max

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

## strings should be pickled
#msg = "hollaaaa"
#if rank == 0:
#    received = world.recv(1)
#    assert received == msg
#    #print "expect: %s element-type:%s got: %s element-type:%s " % (msg, type(msg[0]), received, type(received[0]))
#elif rank == 1:
#    world.send(msg,0)
#
## int lists should be pickled
#msg = range(5)
#if rank == 0:
#    received = world.recv(1)
#    assert received == msg
#    #print "expect: %s element-type:%s got: %s element-type:%s " % (msg, type(msg[0]), received, type(received[0]))
#elif rank == 1:
#    world.send(msg,0)


#
## numpy arrays should NOT be pickled
#msg = numpy.array(range(4))
##msg = range(5)
#received = world.bcast(msg)
#print "%s rank:%i got:%s" % ((msg==received), rank,received)


# numpy arrays should NOT be pickled
msg = numpy.array(range(4))
#msg = range(5)
received = world.gather(msg)
print "%s rank:%i got:%s" % ((msg==received), rank,received)


# numpy arrays should NOT be pickled
#msg = numpy.array(range(4))
#received = world.allreduce(msg,MPI_max)
#print "rank:%i got:%s" % ( rank,received)


#if rank == 0:
#    for r in range(size):
#        world.send(msg,r)
#else:
#    received = world.recv(0)
#    print "rank:%i got:%s" % (rank,received)



mpi.finalize()