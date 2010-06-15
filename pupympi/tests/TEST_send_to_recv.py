#!/usr/bin/env python2.6
# meta-description: Test simple send to recv between 2 processes
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-max_runtime: 5


# Simple pupympi program to test basic blocking send to blocking recieve
# This test is meant to be run with only two processes

 
from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content = "This message was sent"
DUMMY_TAG = 9

if rank == 0:
    # Send
    neighbour = 1
    mpi.MPI_COMM_WORLD.send(content, neighbour, DUMMY_TAG)
    
elif rank == 1: 
    neighbour = 0
    recieved = mpi.MPI_COMM_WORLD.recv(neighbour,DUMMY_TAG)    
else:
    pass

# Close the sockets down nicely
mpi.finalize()
