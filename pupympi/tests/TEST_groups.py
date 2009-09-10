#!/usr/bin/env python2.6

from mpi import MPI
import time

class TestException(Exception): 
    """Custom exception for tests"""
    pass

print "before init"

mpi = MPI()


# we expect the group of MPI_COMM_WORLD to match with the communicator itself
rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

print "---> PROCESS %d/%d" % (rank,size)

cwG = mpi.MPI_COMM_WORLD.group()
print "Group of MPI_COMM_WORLD: %s" % cwG

assert rank is cwG.rank()
assert size is cwG.size()

newG = cwG.incl([rank])
assert newG is not None
print "Incl group %s." % newG

newG = cwG.excl([rank])
assert newG is not None
assert newG.rank() == -1

newG = cwG.excl([0 if rank is 1 else 1])
assert newG is not None
print "Excl group %s." % newG



# Close the sockets down nicely
mpi.finalize()
