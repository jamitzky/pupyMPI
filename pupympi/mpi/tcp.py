import mpi

def isend(comm=None):
    if not comm:
        comm = mpi.MPI_COMM_WORLD

def irecv(comm=None):
    if not comm:
        comm = mpi.MPI_COMM_WORLD
