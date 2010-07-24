# meta-description: A allreduce showing that numpy objects can be transferred with collective operations
# meta-expectedresult: 0
# meta-minprocesses: 10
# meta-max_runtime: 25

from mpi import MPI
mpi = MPI()

try:
    import numpy as np
except ImportError:
    print "NumPy not installed. Will bail from this test. "
    import sys
    mpi.finalize()
    sys.exit()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

local_reduce_data = np.int_([rank,rank*2,rank*4])

expected_data = sum([ np.int_([r, r*2, r*4]) for r in range(size)])

data = world.allreduce(local_reduce_data, sum)

for i in range(3):
    assert data[i] == expected_data[i]

mpi.finalize()
