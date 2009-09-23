from mpi import MPI
from mpi.operations import prod

def fact(n):
    if n == 0:
        return 1
    else:
        return n * fact(n-1)
    
mpi = MPI()

# We start n processes, and try to calculate n!
rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()
dist_fact = mpi.MPI_COMM_WORLD.allreduce(rank+1, prod)

print "I'm rank %d and I also got the result %d. So cool" % (rank, dist_fact)

assert fact(size) == dist_fact

mpi.finalize()
