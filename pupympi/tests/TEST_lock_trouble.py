#!/usr/bin/env python2.6
# META: SKIP
# heavier-duty test

from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD
rank = world.rank()

data = 50*"a"
f = open("/tmp/mpi.local.rank%s.log" % rank, "w")

max_iterations = 5
    

for iterations in xrange(max_iterations):
    if rank == 0: 
        world.send(1, "rank%s,iterations%s" %(rank, iterations), 1)
        # print "%s: %s done sending" % (iterations, c_info.rank)
        msg =  "Iteration %s completed for rank %s\n" % (iterations, rank)
    elif rank == 1: 
        recv = world.recv(0, 1)
        # print "%s, %s done recv: %s" % (iterations, c_info.rank," str(recv)")
        msg =  "Iteration %s completed for rank %s\n" % (iterations, rank)
    else:
        pass
        

    f.write(msg)
    f.flush()
f.write( "Done for rank %d\n" % rank)


f.flush()
f.close()
mpi.finalize()

