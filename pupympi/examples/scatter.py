from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

# Scatter a list with the same number of elements in the 
# list as there are processes in th world communicator

SCATTER_ROOT = 3
if rank == SCATTER_ROOT:
    scatter_data = range(size)
else:
    scatter_data = None

my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
print "Rank %d:" % rank,  my_data

# Scatter a list with 10 times the number of elements
# in the list as there are processes in the world
# communicator. This will give each process a list
# with 10 items in it. 

if rank == SCATTER_ROOT:
    scatter_data = range(size*10)
else:
    scatter_data = None

my_data = world.scatter(scatter_data, root=SCATTER_ROOT)
print "Rank %d:" % rank,  my_data

mpi.finalize()

