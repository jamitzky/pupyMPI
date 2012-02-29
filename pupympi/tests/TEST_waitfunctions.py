#!/usr/bin/env python
# meta-description: Tests waitall returning data
# meta-expectedresult: 0
# meta-minprocesses: 10

from mpi import MPI
    
mpi = MPI()
rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

request_list = []

if mpi.MPI_COMM_WORLD.rank() == 0:
    for i in range(10):
        mpi.MPI_COMM_WORLD.send("Hello World!", 1)

    for i in range(10):
        handle = mpi.MPI_COMM_WORLD.irecv(1)
        request_list.append(handle)

    messages = mpi.MPI_COMM_WORLD.waitall(request_list)
elif mpi.MPI_COMM_WORLD.rank() == 1:
    for i in range(10):
        handle = mpi.MPI_COMM_WORLD.irecv(0)
        request_list.append(handle)

    for i in range(10):
        mpi.MPI_COMM_WORLD.send( "Hello World!", 0)

    messages = mpi.MPI_COMM_WORLD.waitall(request_list)
else:
    pass
    
mpi.finalize()
