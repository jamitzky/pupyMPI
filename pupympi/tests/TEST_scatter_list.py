# meta-description: Test of list scattering
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI
import array

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

#SCATTER_ROOT = 2
SCATTER_ROOT = 0

if rank == SCATTER_ROOT:
    bytearray = array.array('b')
    for i in range(size*4):
        bytearray.append(i)
    #scatter_data = [[x]*2 for x in range(size)]
    #scatter_data = range(size)
    scatter_data = bytearray
else:
    scatter_data = None

my_data = world.scatter(scatter_data, root=SCATTER_ROOT)

mpi.finalize()

#assert my_data == [rank,rank]
