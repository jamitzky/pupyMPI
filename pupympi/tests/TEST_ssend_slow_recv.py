#!/usr/bin/env python2.6
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

f = open(constants.LOGDIR+"mpi.ssend_slow_recv.rank%s.log" % rank, "w")

message = "Just a basic message from %d" % (rank)

DUMMY_TAG = 1

#mpi.MPI_COMM_WORLD.barrier()

if rank == 0: # Send
    neighbour = 1
    f.write("Rank: %d ssending to %d \n" % (rank,neighbour))
    f.flush()
    t1 = time.time()
    
    #mpi.MPI_COMM_WORLD.ssend(neighbour, message, DUMMY_TAG)
    
    handle = mpi.MPI_COMM_WORLD.issend(neighbour, message, DUMMY_TAG)
    print "HANDLE:",handle
    dummy = handle.wait()
    print "DUMMY",dummy
    
    t2 = time.time()
    f.write("Rank: %d sendt synchronized message to %d \n" % (rank,neighbour))
    print (t2-t1)
    #assert ((t2 - t1) > 3)
    
elif rank == 1: # Recieve
    neighbour = 0
    f.write("Rank: %d sleeping before recieving from %d \n" % (rank,neighbour) )
    f.flush()
    #time.sleep(10)
    f.write("Rank: %d recieving from %d \n" % (rank,neighbour) )
    f.flush()
    #recieved = mpi.MPI_COMM_WORLD.recv(neighbour, DUMMY_TAG)    
    #f.write("Rank: %d recieved '%s' \n" % (rank,recieved) )
    #f.flush()

f.write("Done for rank %d\n" % rank)
f.flush()
f.close()

# Close the sockets down nicely
mpi.finalize()
