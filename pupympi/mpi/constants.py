
# Predefined tags
TAG_BCAST = -1
TAG_EMPTY = -2


# NOT IMPLEMENTED: MPI 2.x
# MPI_COMM_SELF

MPI_GROUP_EMPTY = None # gets set later on an empty group to avoid cyclic imports

MPI_IDENT       = 0     # Identical 
MPI_CONGRUENT   = 0     # (only for MPI_COMM_COMPARE) The groups are identical 
MPI_SIMILAR     = 1     # Same members, but in a different order 
MPI_UNEQUAL     = -1    # Different
