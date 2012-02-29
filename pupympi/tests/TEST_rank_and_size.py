#!/usr/bin/env python
# meta-description: Simple pupympi hello world'ish program used for examples
# meta-expectedresult: 0


from mpi import MPI

mpi = MPI()

rank = mpi.MPI_COMM_WORLD.rank()

size = mpi.MPI_COMM_WORLD.size()

print "I am the process with rank %d of %d processes" % (rank, size)

# Close the sockets down nicely
mpi.finalize()
