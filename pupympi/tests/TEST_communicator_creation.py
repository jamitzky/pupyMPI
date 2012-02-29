#!/usr/bin/env python
# meta-description: Test communicator creation and limiting of communicator ids
# meta-expectedresult: 0
# meta-minprocesses: 4


from mpi import MPI
from mpi import constants
import sys

mpi = MPI()

world = mpi.MPI_COMM_WORLD
rank = world.rank()
size = world.size()

# The freshly instantiated world communicator should have an id of 0 and a ceiling of sys.
assert world.id == 0 and world.id_ceiling == sys.maxint

# Create some lists of ranks to use when creating groups
lowers = range(size//2)
uppers = range(size//2,size)

# Create some groups to use when deriving new communicators
# First a group of everyone
wholegroup = world.group()
# Then two groups, half in each
lowerhalf = wholegroup.incl(lowers)
upperhalf = wholegroup.incl(uppers)

# Deriving two seperate communicators from world they should have differing ids
lowercomm = world.comm_create(lowerhalf)
uppercomm = world.comm_create(upperhalf)

# Check lowercomm if you are in it
if lowerhalf.rank() != -1: # A process is not in the group if rank() returns -1
    # lowercomm was created first so it should have maxint/2 as id
    assert lowercomm.id == sys.maxint/2

# Check uppercomm if you are in it
if upperhalf.rank() != -1: # A process is not in the group if rank() returns -1
    # uppercomm was created second so it should have maxint/4 as id
    assert uppercomm.id == sys.maxint/4

# Create two new communicators
newcomm1 = world.comm_create(wholegroup)
newcomm2 = world.comm_create(wholegroup)

# Then three more from latest communicator
newcomm3 = newcomm2.comm_create(wholegroup)
newcomm4 = newcomm2.comm_create(wholegroup)
newcomm5 = newcomm2.comm_create(wholegroup)

# After creating a lot of communicators we should still see the latest communicator
# getting an id equal to the present ceiling of the one it is derived from
assert newcomm5.id == newcomm2.id_ceiling

# After creating a communicator (even one you are not part of) the parent should have lowered ceiling
stored_ceiling = newcomm4.id_ceiling
uppercomm2 = newcomm4.comm_create(upperhalf)
assert stored_ceiling > newcomm4.id_ceiling

# also all the ids should be unique
special_id = lowercomm.id if lowerhalf.rank() != -1 else uppercomm.id
ids = [world.id, newcomm1.id, newcomm2.id, newcomm3.id, newcomm4.id, newcomm5.id, special_id]
assert len(ids) == len(set(ids))

# Close the sockets down nicely
mpi.finalize()
