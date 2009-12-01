#!/usr/bin/env python2.6
# meta-description: test send to irecv with out of order recieving
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-max_runtime: 15


# Rank 0 sends message2 and then message1 to rank 1 who first tries to recive
# message1 (based on tag) and then message2
# That is message1 should be recieved first then message2

import time
from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

content1 = "This is message 1"
content2 = "This is message 2"

DUMMY_TAG = 1
ANOTHER_TAG = 2

if rank == 0:
    neighbour = 1
    # Send
    mpi.MPI_COMM_WORLD.send(neighbour,content2,DUMMY_TAG)
    mpi.MPI_COMM_WORLD.send(neighbour,content1,ANOTHER_TAG)    

elif rank == 1:
    neighbour = 0
    # Recieve
    request1 = mpi.MPI_COMM_WORLD.irecv(neighbour,ANOTHER_TAG)
    recieved1 = request1.wait()

    request2 = mpi.MPI_COMM_WORLD.irecv(neighbour,DUMMY_TAG)
    recieved2 = request2.wait()
    
    assert recieved1 == content1
    assert recieved2 == content2
    
else: 
    pass


# Close the sockets down nicely
mpi.finalize()
