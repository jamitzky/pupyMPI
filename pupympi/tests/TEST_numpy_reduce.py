# meta-description: A simple test and receive showing that numpy object can be transferred without problems
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI
import numpy as np

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

local_reduce_data = np.int_([rank,rank*2,rank*4])

expected_data = sum([ np.int_([r, r*2, r*4]) for r in range(size)])

data = world.allreduce(local_reduce_data, sum)

for i in range(3):
    assert data[i] == expected_data[i]

mpi.finalize()
