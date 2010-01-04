#!/usr/bin/env python2.6
# meta-description: Test waitsome on list of request handles
# meta-expectedresult: 0
# meta-minprocesses: 3

from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD

request_list = []

if world.rank() == 0:
    for i in range(10):
        for rank in range(0, world.size()):
            if rank != 0:
                request = world.irecv(rank)
                request_list.append(request)

    while request_list:
        items =  world.waitsome(request_list)
        print "Waited for %d handles" % len(items)
        for item in items:
            (request, data) = item
            request_list.remove(request)
else:
    for i in range(10):
        world.send(0, "Message")

mpi.finalize()
