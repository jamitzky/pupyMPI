from mpi import MPI
import numpy as np

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()

if rank == 0:
    world.send(1, np.float32(1.0))
    world.send(1, np.int_([1,2,4]))
    world.send(1, np.array([[ 7.,  9.,  7.,  7.,  6.,  3.], [ 5.,  3.,  2.,  8.,  8.,  2.]]))
elif rank == 1:
    for i in range(3):
        r = world.recv(0)
        print type(r), r

mpi.finalize()
