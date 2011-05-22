#!/usr/bin/env python2.6
# meta-description: Test that established socket connections are reused.
# meta-expectedresult: 0
# meta-minprocesses: 2

"""
NOTE: This test deviates from most other tests in that we have to peek into the
internal datastructures to check that the socket pool behaves as expected.

To ensure that the established socket connection between to processes is reused
we check the size of the socket pool directly.

ISSUES:
- In the event of simultaneous connection attempt between two procs we might get
  a duplicate connection in the pool. This manifests itself in a pool size of 2
  when dynamic socket pool is used, if not for the blocking one way operation
  inserted before the iterations start
"""

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
    # First a blocking one way communication to ensure no duplicate connections
    world.send(content, neighbour, DUMMY_TAG)
    
    for _ in xrange(iterations):        
        request = world.isend(content, neighbour, DUMMY_TAG)
        world.recv(neighbour)
        request.wait()  	    

elif rank == 1:
    neighbour = 0
    # First a blocking one way communication to ensure no duplicate connections
    world.recv(neighbour)
    
    for _ in xrange(iterations):        
        request = world.isend(content, neighbour, DUMMY_TAG)
        world.recv(neighbour)
        request.wait()  	    
    
else: # others stay put
    pass

# Dynamic socket pool or static?
if mpi.network.socket_pool.readonly:
    # The static socket pool should contain size-1 connections if connections have been reused properly
    pool_size = len(mpi.network.socket_pool.sockets)
    assert pool_size < size    
else:
    # The dynamic socket pool should contain 1 connection for rank 0 and 1 who have been communicating
    # and no connections for the passive ranks
    pool_size = len(mpi.network.socket_pool.sockets)
    if rank in (0,1):
        assert pool_size == 1
    else:
        assert pool_size == 0

world.barrier()

# Close the sockets down nicely
mpi.finalize()
