import mpi

def isend(comm=None):
    if not comm:
        comm = mpi.MPI_COMM_WORLD

def irecv(destination, content, tag, comm=None):
    if not comm:
        comm = mpi.MPI_COMM_WORLD

    # Check the destination exists
    if not comm.have_rank(destination):
        raise MPIBadAddressException("Not process with rank %d in communicator %s. " % (destination, comm.name))
