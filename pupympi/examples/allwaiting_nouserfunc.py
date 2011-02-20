from mpi import MPI
import time

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

while True:
    time.sleep(1)

mpi.finalize()
