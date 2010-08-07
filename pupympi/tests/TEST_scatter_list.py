# meta-description: Test of list scattering
# meta-expectedresult: 0
# meta-minprocesses: 4

from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

SCATTER_ROOT = 2

if rank == SCATTER_ROOT:
    scatter_data = [[x]*2 for x in range(size)]
else:
    scatter_data = None

my_data = world.scatter(scatter_data, root=SCATTER_ROOT)

mpi.finalize()

assert my_data == [rank,rank]
