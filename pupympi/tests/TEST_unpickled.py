#!/usr/bin/env python
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

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

# strings should be pickled
msg = "hollaaaa"
if rank == 0:
    received = world.recv(1)
    assert received == msg
    #print "expect: %s element-type:%s got: %s element-type:%s " % (msg, type(msg[0]), received, type(received[0]))
elif rank == 1:
    world.send(msg,0)

# int lists should be pickled
msg = range(5)
if rank == 0:
    received = world.recv(1)
    assert received == msg
    #print "expect: %s element-type:%s got: %s element-type:%s " % (msg, type(msg[0]), received, type(received[0]))
elif rank == 1:
    world.send(msg,0)

# numpy arrays should NOT be pickled
msg = numpy.array(range(5))
if rank == 0:
    received = world.recv(1)
    assert numpy.alltrue(received == msg)
    #print "expect: %s element-type:%s got: %s element-type:%s " % (msg, type(msg[0]), received, type(received[0]))
elif rank == 1:
    world.send(msg,0)

# numpy bool array
msg = numpy.array([True,True,False,True,False])
if rank == 0:
    received = world.recv(1)
    assert numpy.alltrue(received == msg)
    #print "expect: %s element-type:%s got: %s element-type:%s " % (msg, type(msg[0]), received, type(received[0]))
elif rank == 1:
    world.send(msg,0)

# numpy float array
msg = numpy.array([i * 1.0/3 for i in xrange(10)])
if rank == 0:
    received = world.recv(1)
    assert numpy.alltrue(received == msg)
    #print "expect: %s element-type:%s got: %s element-type:%s " % (msg, type(msg[0]), received, type(received[0]))
elif rank == 1:
    world.send(msg,0)

# numpy 2D float array
msg = numpy.array([[i,i*2,i * 1.0/3] for i in xrange(10)])
if rank == 0:
    received = world.recv(1)
    assert numpy.alltrue(received == msg)
    #print "expect: %s element-type:%s got: %s element-type:%s " % (msg, type(msg[0]), received, type(received[0]))
elif rank == 1:
    world.send(msg,0)

# numpy 6D float array
msg = numpy.arange(128).reshape(2,2,2,2,4,2)
if rank == 0:
    received = world.recv(1)
    assert numpy.alltrue(received == msg)
    #print "expect: %s element-type:%s got: %s element-type:%s " % (msg, type(msg[0]), received, type(received[0]))
elif rank == 1:
    world.send(msg,0)

# numpy 3D elongated
n = 2**24
msg = numpy.arange((2*n*2),dtype=numpy.int32).reshape(2,n,2)
if rank == 0:
    received = world.recv(1)
    assert numpy.alltrue(received == msg)
    #print "expect: %s element-type:%s got: %s element-type:%s " % (msg, type(msg[0]), received, type(received[0]))
elif rank == 1:
    world.send(msg,0)

# Bytearrays are also not serialized
#msg = bytearray(range(128))
import string
msg = bytearray(string.letters)
if rank == 0:
    received = world.recv(1)
    #print "expect l:%i element-type:%s slice:%s got l:%i element-type:%s slice:%s " % (len(msg), type(msg), msg[0:8], len(received), type(received), received[0:32])
    assert received == msg
elif rank == 1:
    world.send(msg,0)

mpi.finalize()