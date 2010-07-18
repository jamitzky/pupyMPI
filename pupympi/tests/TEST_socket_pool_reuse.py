#!/usr/bin/env python2.6
# meta-description: Test reusing connections when PingPing'ing
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI
from mpi import constants

mpi = MPI()

world = mpi.MPI_COMM_WORLD
rank = world.rank()
size = world.size()

iterations = 100

content = "Message from rank %d" % (rank)
DUMMY_TAG = 1


neighbours = range(size)

if rank == 0:
    neighbour = 1
    for _ in xrange(iterations):        
        request = world.isend(content, neighbour, DUMMY_TAG)
        world.recv(neighbour)
        request.wait()  	    

elif rank == 1:
    neighbour = 0
    for _ in xrange(iterations):        
        request = world.isend(content, neighbour, DUMMY_TAG)
        world.recv(neighbour)
        request.wait()  	    
    
else: # others stay put
    pass
    

world.barrier()

# Close the sockets down nicely
mpi.finalize()
