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
            request_list = world.testsome(handles)
            if request_list:
                # Finish the request
                world.waitall(request_list)
                handles = [ r for r in handles if r not in request_list]

    else:
        world.send(0, "My data", constants.MPI_TAG_ANY)

mpi.finalize()
