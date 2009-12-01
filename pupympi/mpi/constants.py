
# Predefined tags
MPI_TAG_ANY = -1 # public, this and below
MPI_SOURCE_ANY = -2 # to be recognizable

# Other constants. NOTE: These are advisery only
MPI_COMM_NULL = None

# internal tags below. 
TAG_ACK     = -3 
TAG_BCAST   = -4 
TAG_EMPTY   = -5
TAG_BARRIER = -6
TAG_COMM_CREATE = -7
TAG_ALLREDUCE = -8
TAG_REDUCE = -9
TAG_INITIALIZING = -10
TAG_FULL_NETWORK = -11 
TAG_ALLTOALL = -12
TAG_SCATTER = -13
TAG_ALLGATHER = -14
TAG_GATHER = -15
TAG_SCAN = -16

# NOT IMPLEMENTED:
# MPI_COMM_SELF (MPI 2.x)

MPI_GROUP_EMPTY = None # gets set later on an empty group to avoid cyclic imports

MPI_IDENT       = 0     # Identical 
MPI_CONGRUENT   = 0     # (only for MPI_COMM_COMPARE) The groups are identical 
MPI_SIMILAR     = 1     # Same members, but in a different order 
MPI_UNEQUAL     = -1    # Different
MPI_UNDEFINED   = -3    # Like SGI's MPI (http://scv.bu.edu/documentation/tutorials/MPI/alliance/communicators/MPI_Group_rank.html)

JOB_INITIALIZING = -1

# commands used for indicating is this is a system
# message.
CMD_USER = 0
CMD_ABORT = 1
