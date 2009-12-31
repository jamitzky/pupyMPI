# meta-description: A simple test and receive showing that numpy object can be transferred without problems
# meta-expectedresult: 0
# meta-minprocesses: 2

from mpi import MPI
import numpy as np

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

expected_data = [
    np.float32(1.0),
    np.int_([1,2,4]),
    np.array([[ 7.,  9.,  7.,  7.,  6.,  3.],
               [ 5.,  3.,  2.,  8.,  8.,  2.]]),
]

match = True
if rank == 0:
    for ep in expected_data:
        world.send(1, ep)
elif rank == 1:
    for ep in expected_data:
        received = world.recv(0)
        
        if received.shape != ep.shape:
            print 80*"-"
            print "Expected", ep
            print "Received", received
            print 80*"-"

            match = False

assert match

mpi.finalize()
