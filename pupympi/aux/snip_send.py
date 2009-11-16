from mpi import MPI
mpi = MPI()

if mpi.MPI_COMM_WORLD.rank() == 0:
    mpi.MPI_COMM_WORLD.send(1, "Hello World!")
else:
    message = mpi.MPI_COMM_WORLD.recv(0)
    print message