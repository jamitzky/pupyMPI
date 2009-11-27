from mpi import MPI
from numpy import matrix
from mpi.operations import prod

mpi = MPI()

r = mpi.MPI_COMM_WORLD.rank()+1

local_matrix = matrix( [[r, r, r], [r, r, r], [r, r, r] ])

reduced_matrix = mpi.MPI_COMM_WORLD.allreduce(local_matrix, prod)

if r == 1:
    print reduced_matrix

mpi.finalize()
