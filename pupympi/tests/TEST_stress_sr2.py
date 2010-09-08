#!/usr/bin/env python2.6
# meta-description: Multi-process version of stress_sr, with 200 iterations. Processes communicate p2p with neighbours in lockstep: Evens send and odds recieve then vice versa. If odd number of processes are specified the last ranking one is  excluded to avoid deadlock
# meta-expectedresult: 0
# meta-minprocesses: 5
# meta-max_runtime: 120

from mpi import MPI
from mpi import constants

mpi = MPI()
dummydata = ''.join(["a"] * 50)
# Everybody log now
f = open(constants.LOGDIR+"mpi.stress_sr2.rank%s.log" % mpi.MPI_COMM_WORLD.rank(), "w")
maxIterations = 200

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
        f.write("%s: Sending upper to %s " % (rank, upper))
        f.flush()
        mpi.MPI_COMM_WORLD.send( data, upper, 1)

        f.write("%s: Receiving lower to %s " % (rank, lower))
        f.flush()
        recv = mpi.MPI_COMM_WORLD.recv(lower, 1)

        f.write("%s: Sending lower to %s " % (rank, lower))
        f.flush()
        mpi.MPI_COMM_WORLD.send( data, lower, 1)

        f.write("%s: Receiving upper to %s " % (rank, upper))
        f.flush()
        recv = mpi.MPI_COMM_WORLD.recv(upper, 1)

        f.write( "Iteration %s completed for rank %s\n" % (iterations, mpi.MPI_COMM_WORLD.rank()))
        f.flush()
    f.write( "Done for rank %i \n" % rank)
else: # odds
    upper = (rank + 1) % adjSize
    lower = (rank - 1) % adjSize
    for iterations in xrange(maxIterations):
        f.write("%s: Receiving lower to %s" % (rank, lower))
        f.flush()
        recv = mpi.MPI_COMM_WORLD.recv(lower, 1)

        f.write("%s: Sending upper to %s " % (rank, upper))
        f.flush()
        mpi.MPI_COMM_WORLD.send( data, upper,1)

        f.write("%s: Receiving upper to %s " % (rank, upper))
        f.flush()
        recv = mpi.MPI_COMM_WORLD.recv(upper, 1)

        f.write("%s: Sending lower to %s " % (rank, lower))
        f.flush()
        mpi.MPI_COMM_WORLD.send( data, lower, 1)

        f.write( "Iteration %s completed for rank %s\n" % (iterations, mpi.MPI_COMM_WORLD.rank()))
        f.flush()
    f.write( "Done for rank %i \n" % rank)


t2 = mpi.MPI_COMM_WORLD.Wtime()
time = (t2 - t1) 

f.write( "Total time was %s with data length %s, for %i iterations with %i processes participating" % (time, len(data), maxIterations, adjSize))
f.flush()
f.close()
mpi.finalize()


