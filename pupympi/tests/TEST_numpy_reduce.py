# meta-description: A reduce showing that numpy objects can be transferred with collective operations
# meta-expectedresult: 0
# meta-minprocesses: 7
# meta-max_runtime: 25

from mpi import MPI
from mpi.collective.operations import MPI_sum
import sys
from mpi.commons import numpy as np
mpi = MPI()

if not np:
    print "NumPy not installed. Will bail from this test. "
    mpi.finalize()
    sys.exit()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()
ROOT = 3
ROOT = 0

#local_reduce_data = np.int_([rank,rank*2,rank*4])
local_reduce_data = np.int_([[rank,rank]]*3)

#expected_data = sum([ np.int_([r, r*2, r*4]) for r in range(size)])

data = world.reduce(local_reduce_data, MPI_sum, ROOT)

if rank == ROOT:
    print "RECEIVED:%s" % data
#    assert np.alltrue(data == expected_data)
#else:
#    assert data is None
print "RANK %i DONE" %rank    
mpi.finalize()
