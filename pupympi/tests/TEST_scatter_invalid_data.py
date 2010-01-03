# meta-description: Scatter test
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI
from mpi.exceptions import MPIException

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

SCATTER_ROOT = 3

scatter_data = range(size)

try:
    if rank != SCATTER_ROOT:
        world.scatter(scatter_data, root=SCATTER_ROOT)
        assert False
except MPIException:
    pass

mpi.finalize()
