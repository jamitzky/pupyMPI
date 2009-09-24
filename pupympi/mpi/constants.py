
# Predefined tags
MPI_TAG_ANY = -1 # public, this and below
MPI_SOURCE_ANY = -1

TAG_BCAST   = -128 # internal, this and below. Note they do not have to be powers of two, but Rune is being silly.
TAG_EMPTY   = -256
TAG_BARRIER = -512
TAG_COMM_CREATE = -1024
TAG_ALLREDUCE = -2048
TAG_INITIALIZING = -4096 

# NOT IMPLEMENTED:
# MPI_COMM_SELF (MPI 2.x)

MPI_GROUP_EMPTY = None # gets set later on an empty group to avoid cyclic imports

MPI_IDENT       = 0     # Identical 
MPI_CONGRUENT   = 0     # (only for MPI_COMM_COMPARE) The groups are identical 
MPI_SIMILAR     = 1     # Same members, but in a different order 
MPI_UNEQUAL     = -1    # Different
MPI_UNDEFINED   = -3    # Like SGI's MPI (http://scv.bu.edu/documentation/tutorials/MPI/alliance/communicators/MPI_Group_rank.html)

JOB_INITIALIZING = -1
