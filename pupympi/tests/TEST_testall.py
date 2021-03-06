#!/usr/bin/env python
# meta-description: Test of testall
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI
import time

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

handles = []

if rank == 0:
    # Sleep so the sending will be delayed
    time.sleep(3)

for i in range(10):
    if rank == 0:
        world.send(i, 1)
    else:
        handle = world.irecv(0)
        handles.append(handle)

if rank == 1:
    # It will probably not be ready the first time
    ready = world.testall(handles)
    assert not ready 

    # Give time time for the sending to complete
    time.sleep(4)

    # It should be ready now
    ready = world.testall(handles)
    assert ready 


mpi.finalize()
