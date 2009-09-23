from mpi import MPI

mpi = MPI()
if mpi.MPI_COMM_WORLD.rank() == 3:
    mpi.MPI_COMM_WORLD.bcast(3, "Test message")
else:
    message = mpi.MPI_COMM_WORLD.bcast(3)
    print message

mpi.finalize()
