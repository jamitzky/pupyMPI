from mpi import MPI
import time

# We sleep 5 min. This is only to tests some logging iteration
mpi = MPI()
time.sleep(300)

mpi.finalize()
