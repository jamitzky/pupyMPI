# meta-description: A allreduce showing that numpy objects can be transferred with collective operations
# meta-expectedresult: 0
# meta-minprocesses: 10
# meta-max_runtime: 25

from mpi import MPI
from mpi.collective.operations import MPI_sum
import sys
from mpi.commons import numpy as np
mpi = MPI()

if not np:
    print "NumPy not installed. Will bail from this test. "
    mpi.finalize()
    sys.exit()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

local_reduce_data = np.int_([rank,rank*2,rank*4])

expected_data = sum([ np.int_([r, r*2, r*4]) for r in range(size)])

data = world.allreduce(local_reduce_data, MPI_sum)

for i in range(3):
    assert data[i] == expected_data[i]
    
    
# New stuff
local_reduce_data = np.array([rank,rank*2,rank*4])

expected_data = sum([ np.int_([r, r*2, r*4]) for r in range(size)])

data = world.allreduce(local_reduce_data, MPI_sum)

for i in range(3):
    assert data[i] == expected_data[i]

mpi.finalize()
