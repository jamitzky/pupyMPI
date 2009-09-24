#!/usr/bin/env python2.6

# This program tests advanced groups functionality
# NOTE: You tests should run minimum 4 processes

from mpi import MPI
from mpi import constants
import time
import random

class TestException(Exception): 
    """Custom exception for tests"""
    pass

mpi = MPI()


# we expect the group of MPI_COMM_WORLD to match with the communicator itself
rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

print "---> PROCESS %d/%d" % (rank,size)

cwG = mpi.MPI_COMM_WORLD.group()
#print "Group of MPI_COMM_WORLD: %s" % cwG

rip = range(size)

revRip = range(size-1,-1,-1)
allReversed = cwG.incl(revRip)

# Make a group with all but self (unique per process)
allButMe = cwG.excl([rank])

# Make a shuffled group
jumble = range(size)
while jumble == rip or jumble == revRip: # Random is a tricky lover, make sure it's the right kind of random
    random.shuffle(jumble)
allShuffled = cwG.incl(jumble)

# Manual shuffled group
mshuf = [2,1,3,0]
manShuf = cwG.incl(mshuf)

#print "DASHUF " + str(manShuf)

#### Compare tests #####
eq = cwG.compare(cwG)
assert eq is constants.MPI_IDENT

sim = cwG.compare(allReversed)
assert sim is constants.MPI_SIMILAR

uneq = cwG.compare(allButMe)
assert uneq is constants.MPI_UNEQUAL


# FIXME: Remember to compare on shuffled also (manually shuffled?)


#### Translate tests #####

# Translating ranks of allReversed to cwG (=global) ranks in the reverse order
# should yield global order
#tRipAllReverse = cwG.translate_ranks(revRip, allReversed)
#assert tRipAllReverse == rip
#
## Translating the shuffled ranks to cwG should give global order (rip)
#tRipAllShuf = cwG.translate_ranks(jumble, allShuffled)
#assert tRipAllShuf == rip

# TODO: Cross group translation tests need work
"""
# Translating shuffled ranks to reverse order should yield reverse order
tCrossGroup = allReversed.translate_ranks(revRip, allShuffled)
tCrossGroup2 = allShuffled.translate_ranks(jumble, allReversed)
print jumble
print tCrossGroup
print tCrossGroup2
"""


#tSubSet = cwG.translate_ranks([1,2,3], allReversed)
#assert tSubSet == [2,1,0] or size != 4 # Guard extra or-condition in the assert so only tested if size == 4

tSubSet2 = cwG.translate_ranks([0,1,2,3], manShuf)
print "shuf " +str(mshuf)
print "res  " + str(tSubSet2)
#assert tSubSet == [2,1,0] or size != 4 # Guard extra or-condition in the assert so only tested if size == 4


# Close the sockets down nicely
mpi.finalize()
