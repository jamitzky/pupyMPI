# meta-description: Reduce with list as type, prototype for reduce operation to use in benchmarking
# meta-expectedresult: 0
# meta-minprocesses: 4
"""
This test tries a global max over lists of integers
It is a model of the reduce we will use in benchmarking and so when that is done
this test is superflous
"""

from mpi import MPI
from mpi.operations import MPI_prod,MPI_sum, MPI_avg, MPI_min, MPI_max, MPI_list_max

import array, random

def MPI_max_list(input_list):
    """
    This is an operation on lists, so every element in the
    list is a list.
    """
    main_list = []
    for single_list in input_list:
        main_list.extend(single_list)
        
    return max(main_list)
    
#MPI_max_list.partial_data = True

mpi = MPI()
world = mpi.MPI_COMM_WORLD

size = world.size()
rank = world.rank()

#local_data = [2,5,1,(6+rank)]
#local_data = 100 - rank
#local_data = array.array('b')
#for i in range((rank*10)):
#    local_data.append(i)

local_data = range(size)
if rank % 2 == 0:
    local_data.reverse()

result = world.reduce(local_data, MPI_list_max, root=0)
#result = world.reduce(local_data, MPI_max_list, root=0)

random.seed(rank) # Not a very good seed for random, don't use in practice
rolls = [random.randint(1,20) for i in range(6)]
result = world.reduce(rolls, MPI_list_max, 0)
if rank == 0: # Root announces the results
    print "Highest rolls were: ",result
    
mpi.finalize()

#expected_results = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3]
#
#assert expected_results == first_elements 
