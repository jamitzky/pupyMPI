# meta-description: Allreduce with different types
# meta-expectedresult: 0
# meta-minprocesses: 4
"""
This test tries a global min on different Python types 

"""

from mpi import MPI
from mpi.collective.operations import MPI_min

mpi = MPI()
world = mpi.MPI_COMM_WORLD

size = world.size()
rank = world.rank()

root = 2

base = "ibewhereibeat"

# String
# Every rank puts in an A at own index - A is 'smaller' than the other letters
st = base[:rank]+"A"+base[rank+1:]

result1 = world.allreduce(st, MPI_min)
if rank == root:
    assert result1 == "AAAAhereibeat"


# Bytearray
ba = bytearray(base)
# Every rank puts in an A at own index - A is 'smaller' than the other letters
ba[rank] = b'A'
result2 = world.allreduce(ba, MPI_min)

if rank == root:
    assert result2 == bytearray(result1)

# Bool
# Everybody but rank 0 says True but False is smaller
bo = True if rank != 0 else False
result3 = world.allreduce(bo, MPI_min)
if rank == root:
    assert result3 == False

# Int
# Everybody puts in their own rank but max rank goes negative so will be lower
r = rank if rank != (size-1) else -rank
result4 = world.allreduce(r, MPI_min)
if rank == root:
    assert result4 == -(size-1)

# Tuple
# Every rank puts in an A at own 'index' - A is 'smaller' than the other letters
tu = tuple(st) # reuse st string
result5 = world.allreduce(tu, MPI_min)
if rank == root:
    result5 == tuple(result1)

#TODO: Set is commented out for now until we decide the proper semantics of reduction on sets
# Set
#se = set(base)
#se = se.union(range(rank))
#print se
#
#result6 = world.allreduce(se, MPI_min)
#print result6
    
mpi.finalize()
