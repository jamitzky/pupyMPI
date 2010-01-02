from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD
request_list = []

if world.rank() == 0:
    for i in range(10):
        for rank in range(0, world.size()):
            if rank != 0:
                request = world.irecv(rank)
                request_list.append(request)

    while request_list:
        (request, data) =  world.waitany(request_list)
        request_list.remove(request)
else:
    for i in range(10):
        world.send(0, "Message")

mpi.finalize()
