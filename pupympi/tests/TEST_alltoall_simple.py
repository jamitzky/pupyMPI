#!/usr/bin/env python2.6
# meta-description: Test alltoall, while refactoring collective ops
# meta-expectedresult: 0
# meta-minprocesses: 10
# meta-max_runtime: 25

from mpi import MPI


mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()
chunk_size = 4

iterations = 100000000
iterations = 100

data = [str(i)*chunk_size for i in range(size)]

#print "DATA:" + str(data)

recv_data = world.alltoall(data)

for _ in xrange(iterations):
    recv_data = world.alltoall(data)

#if rank == 0:
#    print "\tdata:%s \n\trecv_data:%s" % (data,recv_data)
#print "Rank:%i done (%i iterations)" %(rank,iterations)

expected_data = [ str(rank)*chunk_size for _ in range(size) ]
assert expected_data == recv_data

mpi.finalize()