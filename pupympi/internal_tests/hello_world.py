from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

message = "Hello world (of size:%i), from rank:%i" % (size,rank)

world.send(message,0)

if rank == 0:
    for r in range(size):
        res = world.recv(r)
        print res
        

mpi.finalize()