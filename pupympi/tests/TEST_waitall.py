#!/usr/bin/env python2.6
# meta-description: scan, makes a partial reduce
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

num_sends = 10
handles = []

for i in range(10):
    if rank == 0:
        world.send(1, i)
    else:
        handle = world.irecv(0)
        handles.append(handle)

if rank == 1:
    data = world.waitall(handles)
    assert data == range(10)

mpi.finalize()
