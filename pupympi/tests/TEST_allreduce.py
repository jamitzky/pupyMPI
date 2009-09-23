from mpi import MPI
from mpi.operations import prod

mpi = MPI()

# We start n processes, and try to calculate n!
rank = mpi.MPI_COMM_WORLD.rank()
fact = mpi.MPI_COMM_WORLD.allreduce(rank+1, prod)

print "I'm rank %d and I also got the result %d. So cool" % (rank, fact)

mpi.finalize()
