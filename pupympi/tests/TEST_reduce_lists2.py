# meta-description: Allreduce with list as main type
# meta-expectedresult: 0
# meta-minprocesses: 4
"""
This test tries a global max over lists of integers
"""

from mpi import MPI
from mpi.operations import MPI_prod,MPI_sum, MPI_avg, MPI_min, MPI_max

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

rank = world.rank()

local_data = [[2,5,1,(6+rank)]]
#local_data = 100 - rank

result = world.reduce(local_data, MPI_max_list, root=0)


print "Result:",result
    
mpi.finalize()

#expected_results = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3]
#
#assert expected_results == first_elements 
