from mpi import MPI
from time import time, sleep

mpi = MPI()
world = mpi.MPI_COMM_WORLD

start_time = time()

sleep(2)

end_time = time()

diff = end_time - start_time

# They should not differ by much
global_diff = abs(diff-world.Wtime())

assert global_diff <= 0.1*diff

# Assert that we get a float when we call WTick
tick = world.Wtick()

assert type(tick) == type(1.0)



mpi.finalize()
