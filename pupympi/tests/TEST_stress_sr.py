#!/usr/bin/env python2.6
# meta-description: Cyclic blocking send/receive between two processes. Runs 1000 iterations, and verifies that the data received are correct.
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI
import sys

mpi = MPI()
world = mpi.MPI_COMM_WORLD
rank = world.rank()

data = 50*"a"
f = open("/tmp/cyclic%s.log" % rank, "w")
world.barrier()
max_iterations = 10
t1 = world.Wtime()    

TAG = 13

def gen_msg(rank, iteration):
    return "rank%s,iterations%s" % (rank, iteration)

if rank <= 1:
    other = 1
    if rank == 1:
        other = 0

    for it in xrange(max_iterations):
        if rank == 0: 
            world.send(other, gen_msg(rank, it), TAG)

        recv = world.recv(other, TAG)

        if rank == 1: 
            world.send(other, gen_msg(rank, it), TAG)

        assert recv == gen_msg(other, it)

        f.write("Iteration %s completed for rank %s\n" % (it, rank))
        f.flush()
f.write( "Done for rank %d\n" % rank)

t2 = world.Wtime()
time = (t2 - t1) 

f.write( "Timings were %s for data length %s'n" % (time, len(data)))
f.flush()
f.close()
mpi.finalize()

