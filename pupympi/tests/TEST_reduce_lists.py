# meta-description: Test reduce with list as main type
# meta-expectedresult: 0
# meta-minprocesses: 6
"""
This test tries the reduce operation with lists as the primary datatype.

Every rank builds a list with rank elements. Reduce combined with min should
find the smallest list. Combined with max we should find the biggest list.

TODO: Rewrite this to fit the new reduce semantics
"""

from mpi import MPI

mpi = MPI()
world = mpi.MPI_COMM_WORLD
size = world.size()
rank = world.rank()

max_rank = size - 1
reduce_root = 3 # Just so it's not always 0

local_data = [ rank for x in range(rank) ]
smallest_list = world.reduce(local_data,min,reduce_root)
longest_list = world.reduce(local_data,max,reduce_root)


expected_small = [] # The list from rank 0 should be the smallest
expected_long = [max_rank for x in range(max_rank)] # The list from rank size-1 should be the longest

if rank == reduce_root:
    assert expected_small == smallest_list
    assert expected_long == longest_list














mpi.finalize()
