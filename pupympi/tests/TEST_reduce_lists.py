# meta-description: Allreduce with list as main type
# meta-expectedresult: 0
# meta-minprocesses: 10
"""
This test tries the reduce operation with lists as the primary datatype,
as the internal prepresentation of data in collective operations are list
and we need to make sure that use of lists will not change anything.
"""

from mpi import MPI

def first10(input_list):
    """
    This is an operation on lists, so every elemenet in the
    list is a list. We merge the lists and return the 10 
    first first. 
    """
    main_list = []
    for single_list in input_list:
        main_list.extend(single_list)

    return sorted(main_list)[:10]

first10.partial_data = True

mpi = MPI()
world = mpi.MPI_COMM_WORLD

rank = world.rank()

local_data = [ rank for x in range(3) ]

first_elements = world.allreduce(local_data, first10)

mpi.finalize()

expected_results = [0, 0, 0, 1, 1, 1, 2, 2, 2, 3]

assert expected_results == first_elements 
