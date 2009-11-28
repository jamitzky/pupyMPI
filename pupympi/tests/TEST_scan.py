from mpi import MPI

mpi = MPI()

world = mpi.MPI_COMM_WORLD

rank = world.rank()
size = world.size()

partial_sum = world.scan(rank, sum)

print "%d: Got partial sum of %d" % (rank, partial_sum)

assert partial_sum == sum(range(rank+1))

mpi.finalize()