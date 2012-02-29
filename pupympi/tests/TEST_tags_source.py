#!/usr/bin/env python
# meta-description: Test if tags/sources are handled correctly. Rank 0 sends 5 messages to rank 1 which should receive the first 3 but not the last 2.
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI
from mpi import constants
import time

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()


content = "MSG"

a_real_tag = 1
an_unreal_tag = 2 # not supposed to receive this

if rank == 0:
    # Send
    neighbour = 1
    
    mpi.MPI_COMM_WORLD.send(content, neighbour, a_real_tag)
    mpi.MPI_COMM_WORLD.send(content, neighbour, a_real_tag)
    mpi.MPI_COMM_WORLD.send(content, neighbour, a_real_tag)
    mpi.MPI_COMM_WORLD.send(content, neighbour, a_real_tag)
    
    mpi.MPI_COMM_WORLD.send(content, neighbour, a_real_tag)
    mpi.MPI_COMM_WORLD.send(content, neighbour, a_real_tag)
    

elif rank == 1: 
    # Recieve
    neighbour = 0
    
    # These go through
    recieved = mpi.MPI_COMM_WORLD.recv(neighbour,constants.MPI_TAG_ANY)
    recieved = mpi.MPI_COMM_WORLD.recv(constants.MPI_SOURCE_ANY, a_real_tag)
    recieved = mpi.MPI_COMM_WORLD.recv(constants.MPI_SOURCE_ANY,constants.MPI_TAG_ANY)    
    recieved = mpi.MPI_COMM_WORLD.recv(neighbour,a_real_tag)        
    
    # These do not
    recv_handle_1 = mpi.MPI_COMM_WORLD.irecv(constants.MPI_SOURCE_ANY, an_unreal_tag)    
    recv_handle_2 = mpi.MPI_COMM_WORLD.irecv(1, a_real_tag)    
    
    time.sleep(5) # Make sure the operation do not fail for lack of time
    assert not (recv_handle_1.test() or recv_handle_2.test())
    
else:
    pass

mpi.finalize()
