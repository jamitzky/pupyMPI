#!/usr/bin/env python2.6
# meta-description: Cyclic blocking send/receive between two processes. Runs 1000 iterations, and verifies that the data received are correct.
# meta-expectedresult: 0
# meta-minprocesses: 2

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
        assert recv == data
        # print "%s: %s done receiving %s" % (iterations, c_info.rank, "str(recv)")
        # FIXME Verify data if enabled
        msg =  "Iteration %s completed for rank %s\n" % (iterations, rank)
    elif rank == 1: 
        recv = world.recv(0, 1)
        assert recv == data
        # print "%s, %s done recv: %s" % (iterations, c_info.rank," str(recv)")
        world.send(0, "rank%s,iterations%s" %(rank, iterations), 1)
        # print "%s: %s done sending" % (iterations, c_info.rank)
        # FIXME Verify data if enabled
        msg =  "Iteration %s completed for rank %s\n" % (iterations, rank)
    else: 
        raise Exception("Broken state, too many participating processes.")

    f.write(msg)
    f.flush()
f.write( "Done for rank %d\n" % rank)


t2 = world.Wtime()
time = (t2 - t1) 

f.write( "Timings were %s for data length %s'n" % (time, len(data)))
f.flush()
f.close()
mpi.finalize()

