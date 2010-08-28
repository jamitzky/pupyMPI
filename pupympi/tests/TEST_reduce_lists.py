# meta-description: Reduce over lists
# meta-expectedresult: 0
# meta-minprocesses: 8
"""
This test tries a global max over lists of integers
"""

from mpi import MPI
from mpi.operations import MPI_max

import random

mpi = MPI()
world = mpi.MPI_COMM_WORLD

size = world.size()
rank = world.rank()
root = 2
max_number = size*2

ints = range(max_number+1)
#swap the max with what is at index rank so all lists are not identical
temp = ints[rank]
ints[rank] = ints[max_number]
ints[max_number] = temp

result = world.reduce(ints, MPI_max, 0)

# The expected result is a list of the where the lower half are max_number since
# everyone swapped in a max_number at their rank position. The upper half are
# integers from max rank + 1 up to max_number and then the last integer should be
# max rank since that is the highest rank swapped in there.
expected_result = [(max_number) for _ in range(size)] + range(size,max_number) + [size-1]

if rank == 0: # Root announces the results
    assert expected_result == result
else:
    assert None == result
    
mpi.finalize()
