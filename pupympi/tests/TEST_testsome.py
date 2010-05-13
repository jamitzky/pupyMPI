#!/usr/bin/env python2.6
# meta-description: Test of testsome
# meta-expectedresult: 0
# meta-minprocesses: 4

from mpi import MPI
from mpi import constants
import time

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

WAIT_FAST_ENOUGH = 0.05

handles = []

if rank != 0:
    time.sleep(4)

for i in range(100):
    if rank == 0:
        # This rank receives every message received by the other 
        # processes. 
        for j in range(size-1):
            handle = world.irecv(constants.MPI_SOURCE_ANY) 
            handles.append(handle)

        while handles:
            request_list = world.testsome(handles)
            if request_list:
                # Finish the request
                start_time = time.time()
                world.waitall(request_list)
                end_time = time.time()

                diff_time = end_time - start_time
                assert diff_time < WAIT_FAST_ENOUGH * len(request_list)
                handles = [ r for r in handles if r not in request_list]

    else:
        world.send("My data", 0, constants.MPI_TAG_ANY)

mpi.finalize()
