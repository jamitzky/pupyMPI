#!/usr/bin/env python
# meta-description: Test ssend with delayed matching receive
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-max_runtime: 15

import time
from mpi import MPI
from mpi import constants

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

assert size == 2

f = open(constants.DEFAULT_LOGDIR+"mpi.ssend_slow_recv.rank%s.log" % rank, "w")

message = "Just a basic message from %d" % (rank)

DUMMY_TAG = 1

if rank == 0: # Send
    neighbour = 1
    f.write("Rank: %d ssending to %d \n" % (rank,neighbour))
    f.flush()
    t1 = time.time()
    
    mpi.MPI_COMM_WORLD.ssend(message, neighbour, DUMMY_TAG)
    
    t2 = time.time()
    f.write("Rank: %d sendt synchronized message to %d \n" % (rank,neighbour))
    
    # More than 4 seconds should have elapsed since reciever waits 5 seconds before posting matching recieve
    assert ((t2 - t1) > 4)
    
elif rank == 1: # Recieve
    neighbour = 0
    f.write("Rank: %d sleeping before recieving from %d \n" % (rank,neighbour) )
    f.flush()
    time.sleep(5)
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
