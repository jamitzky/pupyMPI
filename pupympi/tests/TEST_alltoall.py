#!/usr/bin/env python2.6
# meta-description: Test alltoall, sending individual data from all to all
# meta-expectedresult: 0
# meta-minprocesses: 10
# meta-max_runtime: 25

from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

send_data = ["%d --> %d" % (rank, x) for x in range(size)]

recv_data = world.alltoall(send_data)

expected_data = [ '%d --> %d' % (x, rank) for x in range(size)]

try:
    assert recv_data == expected_data
except AssertionError, e:
    #print "Got AssertionError. "
    #print "\tExcepted: %s" % expected_data
    #print "\tReceived data: %s" % recv_data
    raise e

mpi.finalize()