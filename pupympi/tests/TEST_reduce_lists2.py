# meta-description: Reduce with list as type
# meta-expectedresult: 0
# meta-minprocesses: 4
"""
This test tries a global max over lists of integers

It is also the example used in the user documentation, which is why it prints
even though we prefer logging in tests.
"""

from mpi import MPI
from mpi.operations import MPI_list_max

import random

mpi = MPI()
world = mpi.MPI_COMM_WORLD

size = world.size()
rank = world.rank()

local_data = range(size)
if rank % 2 == 0:
    local_data.reverse()

result = world.reduce(local_data, MPI_list_max, root=0)

random.seed(rank) # Not a very good seed for random, don't use in practice
rolls = [random.randint(1,20) for i in range(6)]
result = world.reduce(rolls, MPI_list_max, 0)
if rank == 0: # Root announces the results
    print "Highest rolls were: ",result
    
mpi.finalize()
