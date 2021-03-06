#!/usr/bin/env python
# meta-description: Test alltoall, sending individual data from all to all
# meta-expectedresult: 0
# meta-minprocesses: 10
# meta-max_runtime: 25

from mpi.commons import numpy as np
from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()


### HUMAN READABLE
send_data = ["%d --> %d" % (rank, x) for x in range(size)]
recv_data = world.alltoall(send_data)
expected_data = [ '%d --> %d' % (x, rank) for x in range(size)]
try:
    assert recv_data == expected_data
except AssertionError, e:
    print "Got AssertionError. "
    print "\tExpected: %s" % expected_data
    print "\tReceived data: %s" % recv_data
    raise e

### FLOAT TUPLE
send_data = tuple([ float(r/2) for r in range(size*2) ])
recv_data = world.alltoall(send_data)
expected_data = tuple([ float(rank) for _ in range(size*2)])
assert recv_data == expected_data

#### INT LIST
send_data = [ r/3 for r in range(size*3) ]
recv_data = world.alltoall(send_data)
expected_data = [ rank for _ in range(size*3) ]
assert recv_data == expected_data

### STRING
send_data = ''.join( [ str(r/2) for r in range(size*2) ] )
recv_data = world.alltoall(send_data)
expected_data = str(rank)*size*2
assert recv_data == expected_data

### LISTS OF LISTS
send_data = [ [str(rank),str(rank)] for _ in range(size*2) for _ in range(size)]
recv_data = world.alltoall(send_data)
expected_data = [ [str(r/2),str(r/2)] for r in range(size*2) for _ in range(size)]
assert recv_data == expected_data

#### BYTEARRAY
send_data = bytearray([ r/3 for r in range(size*3) ])
recv_data = world.alltoall(send_data)
expected_data = bytearray([rank]*size*3)
assert recv_data == expected_data

### NUMPY ARRAY
send_data = np.array([rank]*size*2)
recv_data = world.alltoall(send_data)
expected_data = np.array([ r/2 for r in range(size*2)])
assert np.alltrue(recv_data == expected_data)

### NUMPY MULTIDIMENSIONAL ARRAY
send_data = np.array([[rank,42] for _ in range(size)])
recv_data = world.alltoall(send_data)
expected_data = np.array([[r,42] for r in range(size)])
assert np.alltrue(recv_data == expected_data)

mpi.finalize()