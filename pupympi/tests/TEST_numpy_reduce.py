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

sum_of_ranks = sum(range(size))
expected_data = np.int_([sum_of_ranks,sum_of_ranks*2,sum_of_ranks*4]),

data = world.allreduce(local_reduce_data, sum)

for i in range(3):
    print data
    print expected_data
    assert data[i] == expected_data[i]

mpi.finalize()
