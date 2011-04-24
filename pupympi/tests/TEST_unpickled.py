#!/usr/bin/env python2.6
# meta-description: Test sending without serialization
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-max_runtime: 25

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


mpi.finalize()