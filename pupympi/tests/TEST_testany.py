#!/usr/bin/env python2.6
# meta-description: Test case for testany operation. 
# meta-expectedresult: 0
# meta-minprocesses: 4

from mpi import MPI
import time

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

handles = []

for i in range(100):
    if rank == 0:
        # This rank receives every 

        world.send(1, i)
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
