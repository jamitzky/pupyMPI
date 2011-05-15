#!/usr/bin/env python2.6
# meta-description: Basic send and recive over many iterations where communicating parties should remain in sync
# meta-expectedresult: 0
# meta-minprocesses: 2
# meta-max_runtime: 120

from mpi import MPI
from mpi import constants

mpi = MPI()
world = mpi.MPI_COMM_WORLD
rank = world.rank()

DUMMY_TAG = 1

f = open(constants.DEFAULT_LOGDIR+"mpi.lock_trouble.rank%s.log" % rank, "w")

max_iterations = 500

for iterations in xrange(max_iterations):
    if rank == 0: 
        world.send("rank%s,iterations%s" %(rank, iterations), 1, DUMMY_TAG)
        # print "%s: %s done sending" % (iterations, c_info.rank)
        msg =  "Iteration:%s for rank:%s \n" % (iterations, rank)
    elif rank == 1: 
        recv = world.recv(0, DUMMY_TAG)
        # print "%s, %s done recv: %s" % (iterations, c_info.rank," str(recv)")
        msg =  "Iteration:%s for rank:%s got:%s \n" % (iterations, rank, recv)
    else:
        continue

    f.write(msg)
    f.flush()
    
# Test that procs agree on last message (max_iterations)
if rank == 0: 
    world.send("rank%s,iterations%s" %(rank, max_iterations), 1, DUMMY_TAG)
    # print "%s: %s done sending" % (iterations, c_info.rank)
    msg =  "Last iteration: %s for rank:%s \n" % (max_iterations, rank)
    f.write(msg)
    f.flush()
    
elif rank == 1: 
    recv = world.recv(0, DUMMY_TAG)
    # print "%s, %s done recv: %s" % (iterations, c_info.rank," str(recv)")
    msg =  "Last iteration:%s for rank:%s got:%s \n" % (max_iterations, rank, recv)
    # We are only really interested in max_iterations here but the whole string should match also
    goal = ("rank%s,iterations%s" %(0, max_iterations) )
    assert recv == goal
    f.write(msg)
    f.flush()
else:
    pass
    
f.write( "Done for rank %d\n" % rank)
f.flush()
f.close()

mpi.finalize()

