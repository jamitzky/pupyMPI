#!/usr/bin/env python2.6
# META: SKIP
# heavier-duty test

# Processes communicate point to point with neighbours in lockstep
# Evens send and odds recieve then vice versa
# If uneven number of processes are specified the last ranking one is automatically
# excluded so the lockstep scheme does not break down (deadlock)


import time
from mpi import MPI

mpi = MPI()
dummydata = ''.join(["a"] * 50)
# Everybody log now
f = open("/tmp/rank%s.log" % mpi.MPI_COMM_WORLD.rank(), "w")
maxIterations = 10

size = mpi.MPI_COMM_WORLD.size()

# We need an even number of processes so if not we designate last one as idle
if size % 2 != 0:
    adjSize = size -1
else:
    adjSize = size

rank = mpi.MPI_COMM_WORLD.rank()

t1 = mpi.MPI_COMM_WORLD.Wtime() # Time it

data = "message from %i: %s" % (rank, dummydata)

if rank == adjSize: # You are the odd one out so just stay idle
    pass
elif rank % 2 == 0: # evens
    upper = (rank + 1) % adjSize
    lower = (rank - 1) % adjSize
    for iterations in xrange(maxIterations):
        mpi.MPI_COMM_WORLD.send(upper, data, 1)

        recv = mpi.MPI_COMM_WORLD.recv(lower, 1)

        mpi.MPI_COMM_WORLD.send(lower, data, 1)

        recv = mpi.MPI_COMM_WORLD.recv(upper, 1)

        f.write( "Iteration %s completed for rank %s\n" % (iterations, mpi.MPI_COMM_WORLD.rank()))
        f.flush()
    f.write( "Done for rank %i \n" % rank)
else: # odds
    upper = (rank + 1) % adjSize
    lower = (rank - 1) % adjSize
    for iterations in xrange(maxIterations):
        recv = mpi.MPI_COMM_WORLD.recv(lower, 1)

        mpi.MPI_COMM_WORLD.send(upper, data, 1)

mpi = MPI()
data = 50*"a"
f = open("/tmp/rank%s.log" % mpi.MPI_COMM_WORLD.rank(), "w")
#mpi.MPI_COMM_WORLD.barrier()
iterations = 0
maxIterations = 250

t1 = mpi.MPI_COMM_WORLD.Wtime()    
if mpi.MPI_COMM_WORLD.rank() is 0:
    for iterations in xrange(maxIterations):
        mpi.MPI_COMM_WORLD.send(1, data+str(iterations), 1)
        #time.sleep(1)
        # print "%s: %s done sending" % (iterations, c_info.rank)
        recv = mpi.MPI_COMM_WORLD.recv(1, 1)
        # FIXME Verify data if enabled
        f.write( "Iteration %s completed for rank %s (%s)\n" % (iterations, mpi.MPI_COMM_WORLD.rank(), recv))
        f.flush()
    f.write( "Done for rank 0\n")
elif mpi.MPI_COMM_WORLD.rank() is 1: 
    for iterations in xrange(maxIterations):
        recv = mpi.MPI_COMM_WORLD.recv(0, 1)
        #time.sleep(1)
        mpi.MPI_COMM_WORLD.send(0, data, 1)
        # print "%s: %s done sending" % (iterations, c_info.rank)
        # FIXME Verify data if enabled
        f.write( "Iteration %s completed for rank %s (%s)\n" % (iterations, mpi.MPI_COMM_WORLD.rank(), recv))
        f.flush()
    f.write( "Done for rank 1\n")
else: 
    raise Exception("Broken state")


t2 = mpi.MPI_COMM_WORLD.Wtime()
time = (t2 - t1) 

f.write( "Timings were %s for data length %s'n with %i processes participating" % (time, len(data), adjSize))
f.flush()
f.close()
mpi.finalize()

