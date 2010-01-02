from mpi import MPI
import numpy as np

mpi = MPI()
world = mpi.MPI_COMM_WORLD

data = np.int_([1,2,3])

reduced_data = world.allreduce(data, sum)

print reduced_data

mpi.finalize()
