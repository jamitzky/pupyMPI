#!/usr/bin/env python2.6
# META: SKIP
# heavier-duty test

from mpi import MPI

mpi = MPI()
data = ''.join(["a"] * 50)
f = open("/tmp/cyclic%s.log" % mpi.MPI_COMM_WORLD.rank(), "w")
mpi.MPI_COMM_WORLD.barrier()
iterations = 0
max_iterations = 1000
t1 = mpi.MPI_COMM_WORLD.Wtime()    
if mpi.MPI_COMM_WORLD.rank() is 0: 
    while iterations < max_iterations:
        iterations += 1
        mpi.MPI_COMM_WORLD.send(1, "rank%s,iterations%s" %(mpi.MPI_COMM_WORLD.rank(), iterations), 1)
        # print "%s: %s done sending" % (iterations, c_info.rank)
        recv = mpi.MPI_COMM_WORLD.recv(1, 1)
        # print "%s: %s done receiving %s" % (iterations, c_info.rank, "str(recv)")
        # FIXME Verify data if enabled
        msg =  "Iteration %s completed for rank %s\n" % (iterations, mpi.MPI_COMM_WORLD.rank())
        print msg
        f.write(msg)
        f.flush()
    f.write( "Done for rank 0\n")
elif mpi.MPI_COMM_WORLD.rank() is 1: 
    while iterations < max_iterations:
        iterations += 1
        recv = mpi.MPI_COMM_WORLD.recv(0, 1)
        # print "%s, %s done recv: %s" % (iterations, c_info.rank," str(recv)")
        mpi.MPI_COMM_WORLD.send(0, "rank%s,iterations%s" %(mpi.MPI_COMM_WORLD.rank(), iterations), 1)
        # print "%s: %s done sending" % (iterations, c_info.rank)
        # FIXME Verify data if enabled
        msg =  "Iteration %s completed for rank %s\n" % (iterations, mpi.MPI_COMM_WORLD.rank())
        print msg
        f.write(msg)
        f.flush()
    f.write( "Done for rank 1\n")
else: 
    raise Exception("Broken state")


t2 = mpi.MPI_COMM_WORLD.Wtime()
time = (t2 - t1) 

f.write( "Timings were %s for data length %s'n" % (time, len(data)))
f.flush()
f.close()
mpi.finalize()

