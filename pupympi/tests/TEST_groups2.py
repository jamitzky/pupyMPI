#!/usr/bin/env python2.6

# This program tests advanced groups functionality
# NOTE: You tests should run minimum 4 processes

from mpi import MPI
from mpi import constants
from mpi.exceptions import MPINoSuchRankException

import random

class TestException(Exception): 
    """Custom exception for tests"""
    pass

mpi = MPI()


# we expect the group of MPI_COMM_WORLD to match with the communicator itself
rank = mpi.MPI_COMM_WORLD.rank()
size = mpi.MPI_COMM_WORLD.size()

# Take this print out in final version
print "---> PROCESS %d/%d" % (rank,size)

#### Test prerequisites ####

# Some tests do not make  sense if size < 4
assert size > 3

#### Set up groups for tests ####

cwG = mpi.MPI_COMM_WORLD.group()
#print "Group of MPI_COMM_WORLD: %s" % cwG

rip = range(size)

revRip = range(size-1,-1,-1)
allReversed = cwG.incl(revRip)

# Make a group with all but self (this group is unique per process!)
allButMe = cwG.excl([rank])
# Make a group with only self (this group is unique per process!)
onlyMe = cwG.incl([rank])

# Make a shuffled group
jumble = range(size)
# Random is a tricky lover, make sure it's the right kind of random, ie. not
# just one of the others
while jumble == rip or jumble == revRip:
    random.shuffle(jumble)
allShuffled = cwG.incl(jumble)

allButLast = cwG.excl([size-1])

allButFirst = cwG.excl([0])

allButLastAndFirst = cwG.incl(rip[1:-1])

# Make an empty group
emptyGroup = cwG.excl(rip)


#### Compare tests #####

eq = cwG.compare(cwG)
assert eq is constants.MPI_IDENT

sim = cwG.compare(allShuffled)
assert sim is constants.MPI_SIMILAR

uneq = cwG.compare(allButMe)
assert uneq is constants.MPI_UNEQUAL


#### Translate tests #####

# Translating ranks of allReversed to cwG (=global) ranks in the reverse order
# should yield global order
tRipAllReverse = cwG.translate_ranks(revRip, allReversed)
assert tRipAllReverse == rip

# Translating the shuffled ranks to cwG should give global order (rip)
tRipAllShuf = cwG.translate_ranks(jumble, allShuffled)
assert tRipAllShuf == rip

# Cross group translating
t1 = allReversed.translate_ranks(rip, allShuffled)
t2 = allShuffled.translate_ranks(rip, allReversed)
assert allShuffled.translate_ranks(t1, allReversed) == allReversed.translate_ranks(t2, allShuffled)

# Translating subsets
tSubSet = cwG.translate_ranks(rip[1:], allReversed)
assert tSubSet == revRip[1:]

# Translating ranks where one does not translate
tOneMore = cwG.translate_ranks(rip,allButLast)
# Last one in the result should be MPI_UNDEFINED
assert tOneMore == rip[:(size-1)]+[constants.MPI_UNDEFINED]

# Testing exception raising
invalidRanks = rip + [size,size+1]
try:
    tLostInTranslation = cwG.translate_ranks(invalidRanks,allReversed)
except MPINoSuchRankException, e:
    pass
finally:
    gotError = True
assert gotError

    
#### Union tests #####

uniqueUnion = allButMe.union(allButFirst)
# Since allButMe is unique per process so will this union group be unique for each process
# Besides the global rank 0, who is not in the union group, everyone else will
# be added as the last member of the union group (ie. when found in allButFirst)
# and so everyone will have same (max) rank in the union group
if rank == 0:
    assert uniqueUnion.rank() == -1
else:    
    assert uniqueUnion.rank() == size - 1

# Make two groups by excluding and put them together with union
exFirst = allReversed.excl([0]) # 2,1,0
exRest = allReversed.excl(rip[1:]) # 3
reUnion = exRest.union(exFirst) # Unioning "tail on head" should give original group order
eq = reUnion.compare(allReversed)
assert eq is constants.MPI_IDENT

# Test union with an empty group produces same group
allShuffledUnionEmpty = allShuffled.union(emptyGroup)
same1 = allShuffledUnionEmpty.compare(allShuffled)
assert same1 is constants.MPI_IDENT

# Test empty group unioned with other group produces other group
emptyUnionAllShuffled = emptyGroup.union(allShuffled)
same2 = emptyUnionAllShuffled.compare(allShuffled)
assert same2 is constants.MPI_IDENT


#### Intersection tests #####

# Intersection producing all but last and first
allButFirstAndLast = allButFirst.intersection(allButLast)
# Compare with ready made group
ident = allButLastAndFirst.compare(allButFirstAndLast)
assert ident is constants.MPI_IDENT

# Intersection with self is self
sameShuffle = allShuffled.intersection(allShuffled)
ident = sameShuffle.compare(allShuffled)
assert ident is constants.MPI_IDENT

# Intersection with similar is similar
newShuffle = allShuffled.intersection(allReversed)
similar = newShuffle.compare(allReversed)
assert similar is constants.MPI_SIMILAR

# Intersection with empty is empty
newEmpty = emptyGroup.intersection(allButLast)
ident = newEmpty.compare(emptyGroup)
assert ident is constants.MPI_IDENT

# Intersection of disjoint sets is empty
noneCommon = allButMe.intersection(onlyMe)
ident = noneCommon.compare(emptyGroup)
assert ident is constants.MPI_IDENT


#### Difference tests #####

# all except for me = all but me
allButMe2 = cwG.difference(onlyMe)
ident = allButMe.compare(allButMe2)
assert ident is constants.MPI_IDENT

# me except for all = no one
empty = onlyMe.difference(allShuffled)
ident = empty.compare(emptyGroup)
assert ident is constants.MPI_IDENT

# allButLast - allButFirst= onlyFirst
onlyFirst = allButLast.difference(allButFirst)
if rank == 0:
    ident = onlyMe.compare(onlyFirst)
    assert ident is constants.MPI_IDENT
else:
    uneq = onlyMe.compare(onlyFirst)
    assert uneq is constants.MPI_UNEQUAL
    

#print "abm:  " + str(allButMe)
#print "abm2: " + str(allButMe2)


# Close the sockets down nicely
mpi.finalize()
