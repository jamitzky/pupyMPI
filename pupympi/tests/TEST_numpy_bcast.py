# meta-description: Testing the broadcast function with different numpy data types
# meta-expectedresult: 0
# meta-minprocesses: 2

import sys
from mpi import MPI
from mpi.commons import numpy as np
mpi = MPI()

if not np:
    print "NumPy not installed. Will bail from this test. "
    mpi.finalize()
    sys.exit()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

# Broadcast a simple float
send_data = np.float32(1.0)
if rank == 0:
    world.bcast(send_data, 0)
else:
    recv_data = world.bcast(root=0)
    assert recv_data == send_data

# Broadcast an vector
send_data = np.int_([1,2,4])
if rank == 0:
    world.bcast(send_data, 0)
else:
    recv_data = world.bcast(root=0)
    for i in range(len(recv_data)):
        assert recv_data[i] == send_data[i]

# Broadcast a matrix
send_data = np.array([[ 7.,  9.,  7.,  7.,  6.,  3.], [ 5.,  3.,  2.,  8.,  8.,  2.]])
if rank == 0:
    world.bcast(send_data,0)
else:
    recv_data = world.bcast(root=0)
    for x in range(recv_data.shape[0]):
        for y in range(recv_data.shape[1]):
            assert recv_data[x][y] == send_data[x][y]

mpi.finalize()
