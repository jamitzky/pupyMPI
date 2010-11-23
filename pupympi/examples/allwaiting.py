from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

while True:
    sleep(1)
    world.barrier()

mpi.finalize()
