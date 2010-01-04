#!/usr/bin/env python2.6
# meta-description: Test basic synchronized communication. First rank 0 sends then 1 recieves, then vice versa.
# meta-expectedresult: 0
# meta-minprocesses: 2

import time
from mpi import MPI
from mpi import constants

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

assert size == 2

f = open(constants.LOGDIR+"mpi.simple_synchronized_sr.rank%s.log" % rank, "w")

message = "Just a basic message from %d" % (rank)

DUMMY_TAG = 1

if rank == 0: # Send
    neighbour = 1
    f.write("Rank: %d sending to %d \n" % (rank,neighbour))
    f.flush()
    mpi.MPI_COMM_WORLD.ssend(neighbour, message, DUMMY_TAG)
    f.write("Rank: %d succesfully sent to %d \n" % (rank,neighbour) )
    f.flush()
    
elif rank == 1: # Recieve
    neighbour = 0
    f.write("Rank: %d recieving from %d \n" % (rank,neighbour) )
    f.flush()
    recieved = mpi.MPI_COMM_WORLD.recv(neighbour, DUMMY_TAG)    
    f.write("Rank: %d recieved '%s' \n" % (rank,recieved) )
    f.flush()

f.write("Done for rank %d\n" % rank)
f.flush()
f.close()

# Close the sockets down nicely
mpi.finalize()
