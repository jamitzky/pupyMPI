from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

received = world.allgather(rank+1)

assert received == range(1,size+1)
    
mpi.finalize()