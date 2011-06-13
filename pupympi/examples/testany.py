from mpi import MPI
from mpi import constants

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

handles = []

for i in range(100):
    if rank == 0:
        # This rank receives every message received by the other 
        # processes. 
        for j in range(size-1):
            handle = world.irecv(constants.MPI_SOURCE_ANY) 
            handles.append(handle)

        while handles:
            (found, request) = world.testany(handles)
            if found:
                # Finish the request
                request.wait()
                handles.remove(request)

    else:
        world.send(0, "My data", constants.MPI_TAG_ANY)

mpi.finalize()
