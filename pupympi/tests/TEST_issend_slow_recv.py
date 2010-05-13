#!/usr/bin/env python2.6
# meta-description: Test issend with delayed matching receive
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

f = open(constants.LOGDIR+"mpi.issend_slow_recv.rank%s.log" % rank, "w")

message = "Just a basic message from %d" % (rank)

DUMMY_TAG = 1

if rank == 0: # Send
    neighbour = 1
    f.write("Rank: %d issending to %d \n" % (rank,neighbour))
    f.flush()
    
    handle = mpi.MPI_COMM_WORLD.issend(message, neighbour, DUMMY_TAG)
    
    f.write("Rank: %d sendt immediate synchronized message to %d \n" % (rank,neighbour))
    f.flush()
    
    # Since reciever waits 4 seconds before posting matching recieve the first test should fail
    assert not handle.test()
    
    f.write("First test done, rank: %d sleeping before testing again \n" % (rank) )
    time.sleep(5) # By the time we wake up the receiver should have posted matching receive
    
    assert handle.test()
    f.write("Second test done")
    
    # Wait for it - just for the principle of it
    handle.wait()
    
elif rank == 1: # Recieve
    neighbour = 0
    f.write("Rank: %d sleeping before recieving from %d \n" % (rank,neighbour) )
    f.flush()
    time.sleep(4)
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
