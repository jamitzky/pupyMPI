#!/usr/bin/env python2.6
# META: SKIP
# heavier-duty test

from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD
rank = world.rank()

data = 50*"a"
f = open("/tmp/cyclic%s.log" % rank, "w")
world.barrier()
max_iterations = 1000
t1 = world.Wtime()    

for iterations in xrange(max_iterations):
    if rank == 0: 
        world.send(1, "rank%s,iterations%s" %(rank, iterations), 1)
        # print "%s: %s done sending" % (iterations, c_info.rank)
        recv = world.recv(1, 1)
        # print "%s: %s done receiving %s" % (iterations, c_info.rank, "str(recv)")
        # FIXME Verify data if enabled
        msg =  "Iteration %s completed for rank %s\n" % (iterations, rank)
    elif rank == 1: 
        recv = world.recv(0, 1)
        # print "%s, %s done recv: %s" % (iterations, c_info.rank," str(recv)")
        world.send(0, "rank%s,iterations%s" %(rank, iterations), 1)
        # print "%s: %s done sending" % (iterations, c_info.rank)
        # FIXME Verify data if enabled
        msg =  "Iteration %s completed for rank %s\n" % (iterations, rank)
    else: 
        raise Exception("Broken state")

    f.write(msg)
    f.flush()
f.write( "Done for rank %d\n" % rank)


t2 = world.Wtime()
time = (t2 - t1) 

f.write( "Timings were %s for data length %s'n" % (time, len(data)))
f.flush()
f.close()
mpi.finalize()

