#!/usr/bin/env python2.6
# meta-description: Test of testany
# meta-expectedresult: 0
# meta-minprocesses: 4
# meta-max_runtime: 30

from mpi import MPI
from mpi import constants
import time

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

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
            (found, request) = world.testany(handles)
            if found:
                # Finish the request
                start_time = time.time()
                request.wait()
                end_time = time.time()

                diff_time = end_time - start_time
                assert diff_time < 0.05
                handles.remove(request)

    else:
        world.send( "My data", 0, constants.MPI_TAG_ANY)

mpi.finalize()
