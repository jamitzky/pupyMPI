from mpi import MPI
from numpy import array

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()

if rank == 0:
    world.bcast(array([[ 7.,  9.,  7.,  7.,  6.,  3.], [ 5.,  3.,  2.,  8.,  8.,  2.]]), root=0)
else:
    data = world.bcast(root=0)
    print rank, data

mpi.finalize()
