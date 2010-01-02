# meta-description: Scatter test
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

SCATTER_ROOT = 3

if rank == SCATTER_ROOT:
    scatter_data = range(size)
else:
    scatter_data = None

my_data = world.scatter(scatter_data, root=SCATTER_ROOT)

mpi.finalize()

assert my_data == rank
